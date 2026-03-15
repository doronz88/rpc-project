import json
import logging
import plistlib
from collections import namedtuple
from dataclasses import dataclass
from functools import partial
from typing_extensions import Self

import zyncio
from construct import Container
from IPython import get_ipython  # pyright: ignore[reportPrivateImportUsage]
from tqdm import tqdm

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.common import CfSerializable
from rpcclient.clients.darwin.consts import CFPropertyListFormat, CFPropertyListMutabilityOptions, kCFAllocatorDefault
from rpcclient.clients.darwin.objective_c import autorelease_pool, objective_c_class
from rpcclient.clients.darwin.objective_c.objective_c_symbol import ObjectiveCSymbol
from rpcclient.clients.darwin.structs import utsname
from rpcclient.clients.darwin.subsystems.biome import Biome
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
from rpcclient.clients.darwin.symbol import AsyncDarwinSymbol, BaseDarwinSymbol, DarwinSymbol
from rpcclient.core.client import AsyncCoreClient, BaseCoreClient, CoreClient, RemoteCallArg
from rpcclient.core.structs.consts import RTLD_GLOBAL, RTLD_NOW
from rpcclient.core.subsystems.decorator import subsystem
from rpcclient.core.symbol import BaseSymbol
from rpcclient.core.symbols_jar import LazySymbol
from rpcclient.exceptions import CfSerializationError, MissingLibraryError
from rpcclient.protocol.rpc_bridge import AsyncRpcBridge, SyncRpcBridge
from rpcclient.protos.rpc_api_pb2 import MsgId
from rpcclient.utils import cached_async_method


IsaMagic = namedtuple("IsaMagic", "mask value")
ISA_MAGICS = [
    # ARM64
    IsaMagic(mask=0x000003F000000001, value=0x000001A000000001),
    # X86_64
    IsaMagic(mask=0x001F800000000001, value=0x001D800000000001),
]
# Mask for tagged pointer, from objc-internal.h
OBJC_TAG_MASK = 1 << 63

FRAMEWORKS_PATH = "/System/Library/Frameworks"
PRIVATE_FRAMEWORKS_PATH = "/System/Library/PrivateFrameworks"
LIB_PATH = "/usr/lib"

FRAMEWORKS_BLACKLIST = (
    "PowerlogLiteOperators.framework",
    "PowerlogCore.framework",
    "PowerlogHelperdOperators.framework",
    "PowerlogFullOperators.framework",
    "PowerlogAccounting.framework",
    "JavaVM.framework",
    "ActionKit.framework",
    "DashBoard.framework",
    "CoverSheet.framework",
    "StoreKitMacHelper.framework",
    "ReplayKitMacHelper.framework",
    "PassKitMacHelper.framework",
)

logger = logging.getLogger(__name__)


@dataclass
class DyldImage:
    name: str
    base_address: int


class BaseDarwinClient(BaseCoreClient[DarwinSymbolT_co]):
    loaded_objc_classes: list
    _NSPropertyListSerialization: DarwinSymbolT_co
    _CFNullTypeID: object

    def __init__(self, bridge: SyncRpcBridge | AsyncRpcBridge) -> None:
        super().__init__(bridge, RTLD_GLOBAL)
        self._objc_class_cache: dict[str, objective_c_class.Class[DarwinSymbolT_co]] = {}

    @zyncio.zclassmethod
    @classmethod
    async def create(cls, bridge: SyncRpcBridge | AsyncRpcBridge) -> Self:
        self = cls(bridge)
        if (
            await self.dlopen.z(
                "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation",
                RTLD_NOW,
            )
            == 0
        ):
            raise MissingLibraryError("failed to load CoreFoundation")

        self.loaded_objc_classes = []
        self._NSPropertyListSerialization = await self.symbols.objc_getClass.z("NSPropertyListSerialization")
        self._CFNullTypeID = await self.symbols.CFNullGetTypeID.z()

        return self

    @subsystem
    def biome(self) -> Biome[DarwinSymbolT_co]:
        return Biome(self)

    @subsystem
    def duet(self) -> Duet[DarwinSymbolT_co]:
        return Duet(self)

    @subsystem
    def fs(self) -> DarwinFs[DarwinSymbolT_co]:
        return DarwinFs(self)

    @subsystem
    def preferences(self) -> Preferences[DarwinSymbolT_co]:
        return Preferences(self)

    @subsystem
    def processes(self) -> DarwinProcesses[DarwinSymbolT_co]:
        return DarwinProcesses(self)

    @subsystem
    def media(self) -> DarwinMedia[DarwinSymbolT_co]:
        return DarwinMedia(self)

    @subsystem
    def ioregistry(self) -> IORegistry[DarwinSymbolT_co]:
        return IORegistry(self)

    @subsystem
    def xpc(self) -> Xpc[DarwinSymbolT_co]:
        return Xpc(self)

    @subsystem
    def syslog(self) -> Syslog[DarwinSymbolT_co]:
        return Syslog(self)

    @subsystem
    def time(self) -> Time[DarwinSymbolT_co]:
        return Time(self)

    @subsystem
    def hid(self) -> Hid[DarwinSymbolT_co]:
        return Hid(self)

    @subsystem
    def lief(self) -> DarwinLief[DarwinSymbolT_co]:
        return DarwinLief(self)

    @subsystem
    def bluetooth(self) -> Bluetooth[DarwinSymbolT_co]:
        return Bluetooth(self)

    @subsystem
    def core_graphics(self) -> CoreGraphics[DarwinSymbolT_co]:
        return CoreGraphics(self)

    @subsystem
    def keychain(self) -> Keychain[DarwinSymbolT_co]:
        return Keychain(self)

    @subsystem
    def network(self) -> DarwinNetwork[DarwinSymbolT_co]:
        return DarwinNetwork(self)

    @subsystem
    def power(self) -> Power[DarwinSymbolT_co]:
        return Power(self)

    @subsystem
    def location(self) -> Location[DarwinSymbolT_co]:
        return Location(self)

    @zyncio.zmethod
    async def get_images(self) -> list[DyldImage]:
        m = []
        for i in range(await self.symbols._dyld_image_count.z()):
            module_name = await (await self.symbols._dyld_get_image_name.z(i)).peek_str.z()
            base_address = await self.symbols._dyld_get_image_header.z(i)
            m.append(DyldImage(module_name, base_address))
        return m

    @zyncio.zproperty
    async def images(self) -> list[DyldImage]:
        return await self.get_images.z()

    @zyncio.zmethod
    @cached_async_method
    async def get_uname(self) -> Container:
        async with self.safe_calloc.z(utsname.sizeof()) as uname:
            assert await self.symbols.uname.z(uname) == 0
            return await uname.parse.z(utsname)

    @zyncio.zproperty
    async def is_idevice(self) -> bool:
        return (await self.get_uname.z()).machine.startswith("i")

    @zyncio.zmethod
    async def roots(self) -> list[str]:
        """get a list of all accessible darwin roots when used for lookup of files/preferences/..."""
        return ["/", "/var/root"]

    @zyncio.zmethod
    async def showobject(self, object_address: int) -> dict:
        return json.loads((await self.rpc_call.z(MsgId.REQ_SHOW_OBJECT, address=object_address)).description)

    @zyncio.zmethod
    async def showclass(self, class_address: int) -> dict:
        return json.loads((await self.rpc_call.z(MsgId.REQ_SHOW_CLASS, address=class_address)).description)

    @zyncio.zmethod
    async def get_class_list(self) -> dict[str, objective_c_class.Class]:
        ret = await self.rpc_call.z(MsgId.REQ_GET_CLASS_LIST)
        result = {}
        for _class in ret.classes:
            result[_class.name] = objective_c_class.Class(self, self.symbol(_class.address), lazy=True)
        return result

    @zyncio.zmethod
    async def decode_cf(self, symbol: BaseSymbol) -> CfSerializable:
        if await self.symbols.CFGetTypeID.z(symbol) == self._CFNullTypeID:
            return None

        async with self.safe_malloc.z(8) as p_error:
            await p_error.setindex(0, 0)
            objc_data = await self._NSPropertyListSerialization.objc_call.z(
                "dataWithPropertyList:format:options:error:",
                symbol,
                CFPropertyListFormat.kCFPropertyListBinaryFormat_v1_0,
                0,
                p_error,
            )
            if await p_error.getindex(0) != 0:
                raise CfSerializationError()
        if objc_data == 0:
            return None
        count = await self.symbols.CFDataGetLength.z(objc_data)
        async with self.safe_malloc.z(count) as buf:
            await self.symbols.CFDataGetBytes.z(objc_data, 0, count, buf)
            result = plistlib.loads(await buf.peek.z(count))
        await objc_data.objc_call.z("release")
        return result

    @zyncio.zmethod
    async def cf(self, o: CfSerializable) -> DarwinSymbolT_co:
        """construct a CFObject from a given python object"""
        if o is None:
            return await self.symbols.kCFNull.getindex(0)

        plist_bytes = plistlib.dumps(o, fmt=plistlib.FMT_BINARY)
        plist_objc_bytes = await self.symbols.CFDataCreate.z(kCFAllocatorDefault, plist_bytes, len(plist_bytes))
        async with self.safe_malloc.z(8) as p_error:
            await p_error.setindex(0, 0)
            result = await self._NSPropertyListSerialization.objc_call.z(
                "propertyListWithData:options:format:error:",
                plist_objc_bytes,
                CFPropertyListMutabilityOptions.kCFPropertyListMutableContainersAndLeaves,
                0,
                p_error,
            )
            if await p_error.getindex(0) != 0:
                raise CfSerializationError()
            return result

    def objc_symbol(self, address) -> ObjectiveCSymbol[DarwinSymbolT_co]:
        """
        Get objc symbol wrapper for given address
        :param address:
        :return: ObjectiveC symbol object
        """
        return ObjectiveCSymbol(int(address), self)

    @zyncio.zmethod
    async def objc_get_class(self, name: str) -> objective_c_class.Class[DarwinSymbolT_co]:
        """
        Get ObjC class object
        :param name:
        :return:
        """
        if name not in self._objc_class_cache:
            self._objc_class_cache[name] = await objective_c_class.Class.from_class_name(self, name)

        return self._objc_class_cache[name]

    def objc_get_class_lazy(self, name: str) -> "LazyObjectiveCClassSymbol[DarwinSymbolT_co]":
        return LazyObjectiveCClassSymbol(self, name)

    @zyncio.zmethod
    async def is_objc_type(self, symbol: BaseDarwinSymbol) -> bool:
        """
        Test if a given symbol represents an objc object
        :param symbol:
        :return:
        """
        class_info = await (await self.processes.get_self.z()).get_symbol_class_info.z(symbol)
        if class_info == 0:
            return False
        return await (await class_info.objc_call.z("typeName")).py.z() == "ObjC"

    @zyncio.zmethod
    async def rebind_symbols(self, populate_global_scope: bool = True) -> None:
        ip = get_ipython()
        if ip is None:
            raise RuntimeError("ipython is not running")
        logger.debug("rebinding symbols")
        self.loaded_objc_classes.clear()

        # enumerate all loaded objc classes
        for name, class_ in (await self.get_class_list.z()).items():
            self.loaded_objc_classes.append(name)
            if populate_global_scope:
                ip.user_ns[name] = class_

    @zyncio.zmethod
    async def load_framework(self, name: str) -> None:
        lib = await self.dlopen.z(f"{FRAMEWORKS_PATH}/{name}.framework/{name}", RTLD_NOW)
        if lib == 0:
            lib = await self.dlopen.z(f"{PRIVATE_FRAMEWORKS_PATH}/{name}.framework/{name}", RTLD_NOW)
        if lib == 0:
            raise MissingLibraryError(f"failed to load {name}")

    def load_framework_lazy(self, name: str) -> None:
        """Register a framework to be loaded at the beginning of the next RPC call operation."""
        self.pre_rpc_call_hooks.append(partial(self.load_framework.z, name=name))

    @zyncio.zmethod
    async def load_all_libraries(self, rebind_symbols: bool = True) -> None:
        logger.debug(f"loading frameworks: {FRAMEWORKS_PATH}")
        await self._load_frameworks(FRAMEWORKS_PATH)
        logger.debug(f"loading frameworks: {PRIVATE_FRAMEWORKS_PATH}")
        await self._load_frameworks(PRIVATE_FRAMEWORKS_PATH)

        logger.debug(f"loading libraries: {LIB_PATH}")
        for filename in tqdm(await self.fs.listdir.z(LIB_PATH)):
            if not filename.endswith(".dylib"):
                continue
            await self.dlopen.z(f"{LIB_PATH}/{filename}", RTLD_NOW)

        if rebind_symbols:
            await self.rebind_symbols.z()

    async def _load_frameworks(self, frameworks_path: str) -> None:
        for filename in tqdm(await self.fs.listdir.z(frameworks_path)):
            if filename in FRAMEWORKS_BLACKLIST:
                continue
            if "SpringBoard" in filename or "UI" in filename:
                continue
            await self.dlopen.z(f"{frameworks_path}/{filename}/{filename.split('.', 1)[0]}", RTLD_NOW)

    @zyncio.zmethod
    async def create_autorelease_pool_ctx(self) -> autorelease_pool.AutorelesePoolCtx:
        """
        Create `AutoreleasePoolCtx` representing an Objective-C `NSAutoreleasePool`.
        Automatically initialize the new pool, can be used with `with` to
        manage a section which would be drained after exiting.

        :return: `AutorelesePoolCtx`
        """
        return autorelease_pool.AutorelesePoolCtx(self)

    @zyncio.zmethod
    async def get_autorelease_pools(self) -> list[autorelease_pool.AutoreleasePool]:
        """
        Get all autorelease pools currently in the thread.

        :return: List of `AutoreleasePool` instances found in the dump
        """
        return await autorelease_pool.get_autorelease_pools(self)

    @zyncio.zmethod
    async def get_current_autorelease_pool(self) -> autorelease_pool.AutoreleasePool:
        """
        Get the most recently created autorelease pool.

        :return: The last `AutoreleasePool` in the list (most recent)
        :raises IndexError: if no pools are found
        """
        return await autorelease_pool.get_current_autorelease_pool(self)


class LazyObjectiveCClassSymbol(LazySymbol[DarwinSymbolT_co]):
    @cached_async_method
    async def resolve(self) -> DarwinSymbolT_co:
        return await self._client.symbols.objc_getClass.z(self.name)

    @zyncio.zmethod
    async def objc_call(
        self, selector: str, *params: RemoteCallArg, va_list_index: int | None = None
    ) -> DarwinSymbolT_co:
        """call an objc method on a given object and return a symbol"""
        return await (await self.resolve())._objc_call(selector, *params, va_list_index=va_list_index)


class DarwinClient(BaseDarwinClient[DarwinSymbol], CoreClient[DarwinSymbol]):
    def symbol(self, symbol: int) -> DarwinSymbol:
        return DarwinSymbol(symbol, self)


class AsyncDarwinClient(BaseDarwinClient[AsyncDarwinSymbol], AsyncCoreClient[AsyncDarwinSymbol]):
    def symbol(self, symbol: int) -> AsyncDarwinSymbol:
        return AsyncDarwinSymbol(symbol, self)
