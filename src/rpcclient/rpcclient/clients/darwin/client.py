import json
import logging
import plistlib
from collections import namedtuple
from dataclasses import dataclass
from functools import lru_cache
from typing import List

from cached_property import cached_property
from IPython import get_ipython
from tqdm import tqdm

from rpcclient.clients.darwin.common import CfSerializable
from rpcclient.clients.darwin.consts import CFPropertyListFormat, CFPropertyListMutabilityOptions, kCFAllocatorDefault
from rpcclient.clients.darwin.objective_c import autorelease_pool, objective_c_class
from rpcclient.clients.darwin.objective_c.objective_c_symbol import ObjectiveCSymbol
from rpcclient.clients.darwin.structs import utsname
from rpcclient.clients.darwin.subsystems.bluetooth import Bluetooth
from rpcclient.clients.darwin.subsystems.core_graphics import CoreGraphics
from rpcclient.clients.darwin.subsystems.darwin_lief import DarwinLief
from rpcclient.clients.darwin.subsystems.duet import Duet
from rpcclient.clients.darwin.subsystems.fs import DarwinFs
from rpcclient.clients.darwin.subsystems.hid import Hid
from rpcclient.clients.darwin.subsystems.ioregistry import IORegistry
from rpcclient.clients.darwin.subsystems.keychain import Keychain
from rpcclient.clients.darwin.subsystems.location import Location
from rpcclient.clients.darwin.subsystems.media import DarwinMedia
from rpcclient.clients.darwin.subsystems.network import DarwinNetwork
from rpcclient.clients.darwin.subsystems.power import Power
from rpcclient.clients.darwin.subsystems.preferences import Preferences
from rpcclient.clients.darwin.subsystems.processes import DarwinProcesses
from rpcclient.clients.darwin.subsystems.syslog import Syslog
from rpcclient.clients.darwin.subsystems.time import Time
from rpcclient.clients.darwin.subsystems.xpc import Xpc
from rpcclient.clients.darwin.symbol import DarwinSymbol
from rpcclient.core.client import CoreClient
from rpcclient.core.structs.consts import RTLD_GLOBAL, RTLD_NOW
from rpcclient.core.subsystems.decorator import subsystem
from rpcclient.core.symbol import Symbol
from rpcclient.exceptions import CfSerializationError, MissingLibraryError
from rpcclient.protocol.rpc_bridge import RpcBridge
from rpcclient.protos.rpc_api_pb2 import MsgId

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


class DarwinClient(CoreClient):
    def __init__(self, bridge: RpcBridge):
        super().__init__(bridge, dlsym_global_handle=RTLD_GLOBAL)

        if 0 == self.dlopen('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation', RTLD_NOW):
            raise MissingLibraryError('failed to load CoreFoundation')

        self.loaded_objc_classes = []
        self._NSPropertyListSerialization = self.symbols.objc_getClass('NSPropertyListSerialization')
        self._CFNullTypeID = self.symbols.CFNullGetTypeID()

    @subsystem
    def duet(self) -> Duet:
        return Duet(self)

    @subsystem
    def fs(self) -> DarwinFs:
        return DarwinFs(self)

    @subsystem
    def preferences(self) -> Preferences:
        return Preferences(self)

    @subsystem
    def processes(self) -> DarwinProcesses:
        return DarwinProcesses(self)

    @subsystem
    def media(self) -> DarwinMedia:
        return DarwinMedia(self)

    @subsystem
    def ioregistry(self) -> IORegistry:
        return IORegistry(self)

    @subsystem
    def xpc(self) -> Xpc:
        return Xpc(self)

    @subsystem
    def syslog(self) -> Syslog:
        return Syslog(self)

    @subsystem
    def time(self) -> Time:
        return Time(self)

    @subsystem
    def hid(self) -> Hid:
        return Hid(self)

    @subsystem
    def lief(self) -> DarwinLief:
        return DarwinLief(self)

    @subsystem
    def bluetooth(self) -> Bluetooth:
        return Bluetooth(self)

    @subsystem
    def core_graphics(self) -> CoreGraphics:
        return CoreGraphics(self)

    @subsystem
    def keychain(self) -> Keychain:
        return Keychain(self)

    @subsystem
    def network(self) -> DarwinNetwork:
        return DarwinNetwork(self)

    @subsystem
    def power(self) -> Power:
        return Power(self)

    @subsystem
    def location(self) -> Location:
        return Location(self)

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
        return json.loads(self.rpc_call(MsgId.REQ_SHOW_OBJECT, address=object_address).description)

    def showclass(self, class_address: Symbol) -> dict:
        return json.loads(self.rpc_call(MsgId.REQ_SHOW_CLASS, address=class_address).description)

    def get_class_list(self) -> dict[str, objective_c_class.Class]:
        ret = self.rpc_call(MsgId.REQ_GET_CLASS_LIST)
        result = {}
        for _class in ret.classes:
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

    def rebind_symbols(self, populate_global_scope=True) -> None:
        ip = get_ipython()
        if ip is None:
            raise RuntimeError('ipython is not running')
        logger.debug('rebinding symbols')
        self.loaded_objc_classes.clear()

        # enumerate all loaded objc classes
        for name, class_ in self.get_class_list().items():
            self.loaded_objc_classes.append(name)
            if populate_global_scope:
                ip.user_ns[name] = class_

    def load_framework(self, name: str) -> None:
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
