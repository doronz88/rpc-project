import ast
import builtins
import json
import logging
import plistlib
import typing
from collections import namedtuple
from dataclasses import dataclass
from functools import lru_cache
from typing import List

from cached_property import cached_property
from tqdm import tqdm

from rpcclient.client import Client
from rpcclient.darwin import autorelease_pool, objective_c_class
from rpcclient.darwin.bluetooth import Bluetooth
from rpcclient.darwin.common import CfSerializable
from rpcclient.darwin.consts import CFPropertyListFormat, CFPropertyListMutabilityOptions, kCFAllocatorDefault
from rpcclient.darwin.core_graphics import CoreGraphics
from rpcclient.darwin.darwin_lief import DarwinLief
from rpcclient.darwin.fs import DarwinFs
from rpcclient.darwin.hid import Hid
from rpcclient.darwin.ioregistry import IORegistry
from rpcclient.darwin.keychain import Keychain
from rpcclient.darwin.location import Location
from rpcclient.darwin.media import DarwinMedia
from rpcclient.darwin.network import DarwinNetwork
from rpcclient.darwin.objective_c_symbol import ObjectiveCSymbol
from rpcclient.darwin.power import Power
from rpcclient.darwin.preferences import Preferences
from rpcclient.darwin.processes import DarwinProcesses
from rpcclient.darwin.structs import utsname
from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.darwin.syslog import Syslog
from rpcclient.darwin.time import Time
from rpcclient.darwin.xpc import Xpc
from rpcclient.exceptions import CfSerializationError, GettingObjectiveCClassError, MissingLibraryError
from rpcclient.protobuf_bridge import CmdGetClassList, CmdShowClass, CmdShowObject
from rpcclient.structs.consts import RTLD_GLOBAL, RTLD_NOW
from rpcclient.symbol import Symbol
from rpcclient.symbols_jar import SymbolsJar

IsaMagic = namedtuple('IsaMagic', 'mask value')
ISA_MAGICS = [
    # ARM64
    IsaMagic(mask=0x000003f000000001, value=0x000001a000000001),
    # X86_64
    IsaMagic(mask=0x001f800000000001, value=0x001d800000000001),
]
# Mask for tagged pointer, from objc-internal.h
OBJC_TAG_MASK = (1 << 63)

FRAMEWORKS_PATH = '/System/Library/Frameworks'
PRIVATE_FRAMEWORKS_PATH = '/System/Library/PrivateFrameworks'
LIB_PATH = '/usr/lib'

FRAMEWORKS_BLACKLIST = (
    'PowerlogLiteOperators.framework', 'PowerlogCore.framework', 'PowerlogHelperdOperators.framework',
    'PowerlogFullOperators.framework', 'PowerlogAccounting.framework', 'JavaVM.framework', 'ActionKit.framework',
    'DashBoard.framework', 'CoverSheet.framework', 'StoreKitMacHelper.framework', 'ReplayKitMacHelper.framework',
    'PassKitMacHelper.framework')

logger = logging.getLogger(__name__)


@dataclass
class DyldImage:
    name: str
    base_address: int


class DarwinClient(Client):
    def __init__(self, sock, sysname: str, arch, create_socket_cb: typing.Callable):
        super().__init__(sock, sysname, arch, create_socket_cb, dlsym_global_handle=RTLD_GLOBAL)

    def _init_process_specific(self):
        super()._init_process_specific()

        if 0 == self.dlopen('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation', RTLD_NOW):
            raise MissingLibraryError('failed to load CoreFoundation')

        self.fs = DarwinFs(self)
        self.preferences = Preferences(self)
        self.processes = DarwinProcesses(self)
        self.media = DarwinMedia(self)
        self.ioregistry = IORegistry(self)
        self.location = Location(self)
        self.xpc = Xpc(self)
        self.syslog = Syslog(self)
        self.time = Time(self)
        self.hid = Hid(self)
        self.lief = DarwinLief(self)
        self.bluetooth = Bluetooth(self)
        self.core_graphics = CoreGraphics(self)
        self.keychain = Keychain(self)
        self.network = DarwinNetwork(self)
        self.power = Power(self)
        self.loaded_objc_classes = []
        self._NSPropertyListSerialization = self.symbols.objc_getClass('NSPropertyListSerialization')
        self._CFNullTypeID = self.symbols.CFNullGetTypeID()

    def interactive(self, additional_namespace: typing.Optional[dict] = None):
        if additional_namespace is None:
            additional_namespace = {}
        additional_namespace['CFSTR'] = self.cf
        super().interactive(additional_namespace=additional_namespace)

    @property
    def errno(self) -> int:
        p_error = self.symbols['__error']()
        p_error.item_size = 4
        return p_error[0]

    @errno.setter
    def errno(self, value: int) -> None:
        p_error = self.symbols['__error']()
        p_error.item_size = 4
        p_error[0] = value

    @property
    def images(self) -> list[DyldImage]:
        m = []
        for i in range(self.symbols._dyld_image_count()):
            module_name = self.symbols._dyld_get_image_name(i).peek_str()
            base_address = self.symbols._dyld_get_image_header(i)
            m.append(
                DyldImage(module_name, base_address)
            )
        return m

    @cached_property
    def uname(self):
        with self.safe_calloc(utsname.sizeof()) as uname:
            assert 0 == self.symbols.uname(uname)
            return utsname.parse_stream(uname)

    @cached_property
    def is_idevice(self):
        return self.uname.machine.startswith('i')

    @property
    def roots(self) -> list[str]:
        """ get a list of all accessible darwin roots when used for lookup of files/preferences/... """
        return ['/', '/var/root']

    def showobject(self, object_address: Symbol) -> dict:
        response = self._sock.send_recv(CmdShowObject(address=object_address))
        return json.loads(response.description)

    def showclass(self, class_address: Symbol) -> dict:
        response = self._sock.send_recv(CmdShowClass(address=class_address))
        return json.loads(response.description)

    def get_class_list(self) -> dict[str, objective_c_class.Class]:
        result = {}
        command = CmdGetClassList()
        response = self._sock.send_recv(command)
        for _class in response.classes:
            result[_class.name] = objective_c_class.Class(self, self.symbol(_class.address), lazy=True)
        return result

    def symbol(self, symbol: int):
        """ at a symbol object from a given address """
        return DarwinSymbol.create(symbol, self)

    def decode_cf(self, symbol: Symbol) -> CfSerializable:
        if self.symbols.CFGetTypeID(symbol) == self._CFNullTypeID:
            return None

        with self.safe_malloc(8) as p_error:
            p_error[0] = 0
            objc_data = self._NSPropertyListSerialization.objc_call('dataWithPropertyList:format:options:error:',
                                                                    symbol,
                                                                    CFPropertyListFormat.kCFPropertyListBinaryFormat_v1_0,
                                                                    0, p_error)
            if p_error[0] != 0:
                raise CfSerializationError()
        if objc_data == 0:
            return None
        count = self.symbols.CFDataGetLength(objc_data)
        result = plistlib.loads(self.symbols.CFDataGetBytePtr(objc_data).peek(count))
        objc_data.objc_call('release')
        return result

    def cf(self, o: CfSerializable) -> DarwinSymbol:
        """ construct a CFObject from a given python object """
        if o is None:
            return self.symbols.kCFNull[0]

        plist_bytes = plistlib.dumps(o, fmt=plistlib.FMT_BINARY)
        plist_objc_bytes = self.symbols.CFDataCreate(kCFAllocatorDefault, plist_bytes, len(plist_bytes))
        with self.safe_malloc(8) as p_error:
            p_error[0] = 0
            result = self._NSPropertyListSerialization.objc_call(
                'propertyListWithData:options:format:error:',
                plist_objc_bytes,
                CFPropertyListMutabilityOptions.kCFPropertyListMutableContainersAndLeaves,
                0, p_error)
            if p_error[0] != 0:
                raise CfSerializationError()
            return result

    def objc_symbol(self, address) -> ObjectiveCSymbol:
        """
        Get objc symbol wrapper for given address
        :param address:
        :return: ObjectiveC symbol object
        """
        return ObjectiveCSymbol.create(int(address), self)

    @lru_cache(maxsize=None)
    def objc_get_class(self, name: str):
        """
        Get ObjC class object
        :param name:
        :return:
        """
        return objective_c_class.Class.from_class_name(self, name)

    def is_objc_type(self, symbol: DarwinSymbol) -> bool:
        """
        Test if a given symbol represents an objc object
        :param symbol:
        :return:
        """
        class_info = self.processes.get_self().get_symbol_class_info(symbol)
        if class_info == 0:
            return False
        return 'ObjC' == class_info.objc_call('typeName').py()

    def _add_global(self, name: str, value) -> None:
        super()._add_global(name, value)
        globals()[name] = value

    def _ipython_run_cell_hook(self, info):
        """
        Enable lazy loading for symbols
        :param info: IPython's CellInf4o object
        """
        super()._ipython_run_cell_hook(info)

        for node in ast.walk(ast.parse(info.raw_cell)):
            if not isinstance(node, ast.Name):
                # we are only interested in names
                continue

            if node.id in locals():
                continue

            global_var = globals().get(node.id)
            if global_var is not None:
                if isinstance(global_var, objective_c_class.Class) and global_var.name == '':
                    # reload lazy classes right before actual use
                    global_var.reload()
                continue

            if node.id in dir(builtins):
                continue

            if not hasattr(SymbolsJar, node.id):
                # ignore SymbolsJar properties
                try:
                    symbol = self.objc_get_class(node.id)
                except GettingObjectiveCClassError:
                    pass
                else:
                    self._add_global(
                        node.id,
                        symbol
                    )

    def rebind_symbols(self, populate_global_scope=True) -> None:
        logger.debug('rebinding symbols')
        self.loaded_objc_classes.clear()

        # enumerate all loaded objc classes
        for name, class_ in self.get_class_list().items():
            self.loaded_objc_classes.append(name)
            if populate_global_scope:
                self._add_global(
                    name,
                    class_
                )

    def load_framework(self, name: str) -> DarwinSymbol:
        lib = self.dlopen(f'{FRAMEWORKS_PATH}/{name}.framework/{name}', RTLD_NOW)
        if lib == 0:
            lib = self.dlopen(f'{PRIVATE_FRAMEWORKS_PATH}/{name}.framework/{name}', RTLD_NOW)
        if lib == 0:
            raise MissingLibraryError(f'failed to load {name}')

    def load_all_libraries(self, rebind_symbols=True) -> None:
        logger.debug(f'loading frameworks: {FRAMEWORKS_PATH}')
        self._load_frameworks(FRAMEWORKS_PATH)
        logger.debug(f'loading frameworks: {PRIVATE_FRAMEWORKS_PATH}')
        self._load_frameworks(PRIVATE_FRAMEWORKS_PATH)

        logger.debug(f'loading libraries: {LIB_PATH}')
        for filename in tqdm(self.fs.listdir(LIB_PATH)):
            if not filename.endswith('.dylib'):
                continue
            self.dlopen(f'{LIB_PATH}/{filename}', RTLD_NOW)

        if rebind_symbols:
            self.rebind_symbols()

    def _load_frameworks(self, frameworks_path: str):
        for filename in tqdm(self.fs.listdir(frameworks_path)):
            if filename in FRAMEWORKS_BLACKLIST:
                continue
            if 'SpringBoard' in filename or 'UI' in filename:
                continue
            self.dlopen(f'{frameworks_path}/{filename}/{filename.split(".", 1)[0]}', RTLD_NOW)

    def create_autorelease_pool_ctx(self) -> autorelease_pool.AutorelesePoolCtx:
        """
        Create `AutoreleasePoolCtx` representing an Objective-C `NSAutoreleasePool`.
        Automatically initialize the new pool, can be used with `with` to
        manage a section which would be drained after exiting.

        :return: `AutorelesePoolCtx`
        """
        return autorelease_pool.AutorelesePoolCtx(self)

    def get_autorelease_pools_raw(self) -> str:
        """
        Get raw autorelease pool dump from stderr using `_objc_autoreleasePoolPrint`, handling known off-by-one bug.

        :return: Full raw text of all pools printed to stderr
        """
        return autorelease_pool.get_autorelease_pools_str(self)

    def get_autorelease_pools(self) -> List[autorelease_pool.AutoreleasePool]:
        """
        Get all autorelease pools currently in the thread.

        :return: List of `AutoreleasePool` instances found in the dump
        """
        return autorelease_pool.get_autorelease_pools(self)

    def get_current_autorelease_pool(self) -> autorelease_pool.AutoreleasePool:
        """
        Get the most recently created autorelease pool.

        :return: The last `AutoreleasePool` in the list (most recent)
        :raises IndexError: if no pools are found
        """
        return autorelease_pool.get_current_autorelease_pool(self)
