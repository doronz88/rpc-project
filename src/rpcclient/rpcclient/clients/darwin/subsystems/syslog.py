import datetime
import logging
import re
from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT, DarwinSymbolT_co
from rpcclient.clients.darwin.consts import OsLogLevel
from rpcclient.clients.darwin.subsystems.cfpreferences import GLOBAL_DOMAIN, kCFPreferencesAnyHost
from rpcclient.clients.darwin.subsystems.processes import Process
from rpcclient.core._types import ClientBound
from rpcclient.core.structs.consts import SIGKILL
from rpcclient.exceptions import BadReturnValueError, HarGlobalNotFoundError, MissingLibraryError
from rpcclient.utils import cached_async_method


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient

MOV_RDI_RBX = b"\x48\x89\xdf"
XOR_ESI_ESI = b"\x31\xf6"
MOV_EDX_0A = b"\xba\x0a\x00\x00"
INTEL_PATTERN = MOV_RDI_RBX + XOR_ESI_ESI + MOV_EDX_0A + b"\x00"

MOV_X0_X9 = b"\xe0\x03\x13\xaa"
MOV_X1_0 = b"\x01\x00\x80\xd2"
MOV_W2_0XA = b"\x42\x01\x80\x52"
ARM_PATTERN = MOV_X0_X9 + MOV_X1_0 + MOV_W2_0XA

logger = logging.getLogger(__name__)


class OsLogPreferencesBase(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]", obj: DarwinSymbolT_co) -> None:
        self._client = client
        self._object: DarwinSymbolT_co = obj

    @zyncio.zproperty
    async def name(self) -> str:
        return await (await self._object.objc_call.z("name")).py.z(str)

    @zyncio.zproperty
    async def _persisted_level(self) -> OsLogLevel:
        return OsLogLevel(await self._object.objc_call.z("persistedLevel"))

    @_persisted_level.setter
    async def persisted_level(self, value: OsLogLevel) -> None:
        await self._object.objc_call.z("setPersistedLevel:", value)

    @zyncio.zproperty
    async def default_persisted_level(self) -> OsLogLevel:
        return OsLogLevel(await self._object.objc_call.z("defaultPersistedLevel"))

    @zyncio.zproperty
    async def _enabled_level(self) -> OsLogLevel:
        return OsLogLevel(await self._object.objc_call.z("enabledLevel"))

    @_enabled_level.setter
    async def enabled_level(self, value: OsLogLevel) -> None:
        await self._object.objc_call.z("setEnabledLevel:", value)

    @zyncio.zproperty
    async def default_enabled_level(self) -> OsLogLevel:
        return OsLogLevel(await self._object.objc_call.z("defaultEnabledLevel"))

    @zyncio.zproperty
    async def _verbosity_description(self) -> str:
        enabled_level = await type(self).enabled_level(self)
        persisted_level = await type(self).persisted_level(self)
        return (
            f"ENABLED_LEVEL:{enabled_level.name}({enabled_level.value}) "
            f"PERSISTED_LEVEL:{persisted_level.name}({persisted_level.value})"
        )

    @zyncio.zmethod
    async def reset(self) -> None:
        await self._object.objc_call.z("reset")

    def __repr__(self) -> str:
        if zyncio.is_sync(self):
            return f"<{self.__class__.__name__} NAME:{self.name} {self._verbosity_description}>"
        return f"<{self.__class__.__name__} (async)>"


class OsLogPreferencesCategory(OsLogPreferencesBase[DarwinSymbolT_co]):
    @staticmethod
    async def create(
        client: "BaseDarwinClient[DarwinSymbolT]", category: str, subsystem: int
    ) -> "OsLogPreferencesCategory[DarwinSymbolT]":
        obj = await (
            await (await client.symbols.objc_getClass.z("OSLogPreferencesCategory")).objc_call.z("alloc")
        ).objc_call.z("initWithName:subsystem:", await client.cf.z(category), subsystem)
        return OsLogPreferencesCategory(client, obj)

    @zyncio.zproperty
    async def name(self) -> str:
        return await (await self._object.objc_call.z("name")).py.z(str)


class OsLogPreferencesSubsystem(OsLogPreferencesBase[DarwinSymbolT_co]):
    @staticmethod
    async def create(
        client: "BaseDarwinClient[DarwinSymbolT]", subsystem: str
    ) -> "OsLogPreferencesSubsystem[DarwinSymbolT]":
        obj = await (
            await (await client.symbols.objc_getClass.z("OSLogPreferencesSubsystem")).objc_call.z("alloc")
        ).objc_call.z("initWithName:", await client.cf.z(subsystem))
        return OsLogPreferencesSubsystem(client, obj)

    @zyncio.zproperty
    async def category_strings(self) -> list[str]:
        return await (await self._object.objc_call.z("categories")).py.z(list)

    @zyncio.zproperty
    async def categories(self) -> list[OsLogPreferencesCategory]:
        result = []
        for name in await type(self).category_strings(self):
            result.append(await self.get_category.z(name))
        return result

    @zyncio.zmethod
    async def get_category(self, name: str) -> OsLogPreferencesCategory:
        return await OsLogPreferencesCategory.create(self._client, name, self._object)


class OsLogPreferencesManager(OsLogPreferencesBase[DarwinSymbolT_co]):
    @staticmethod
    async def create(client: "BaseDarwinClient[DarwinSymbolT]") -> "OsLogPreferencesManager[DarwinSymbolT]":
        obj = await (await client.symbols.objc_getClass.z("OSLogPreferencesManager")).objc_call.z("sharedManager")
        return OsLogPreferencesManager(client, obj)

    @zyncio.zproperty
    async def subsystem_strings(self) -> list[str]:
        return await (await self._object.objc_call.z("subsystems")).py.z(list)

    @zyncio.zproperty
    async def subsystems(self) -> list[OsLogPreferencesSubsystem]:
        result = []
        for name in await type(self).subsystem_strings(self):
            result.append(await self.get_subsystem.z(name))
        return result

    @zyncio.zmethod
    async def get_subsystem(self, name: str) -> OsLogPreferencesSubsystem[DarwinSymbolT_co]:
        return await OsLogPreferencesSubsystem.create(self._client, name)


class Syslog(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """manage syslog"""

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client
        self._client.load_framework_lazy("LoggingSupport")

    @zyncio.zproperty
    @cached_async_method
    async def preferences_manager(self) -> OsLogPreferencesManager[DarwinSymbolT_co]:
        return await OsLogPreferencesManager.create(self._client)

    @cached_async_method
    async def _cfnetwork_base(self) -> int:
        await self._client.load_framework.z("CFNetwork")
        try:
            return next(
                image
                for image in await self._client.get_images.z()
                if image.name.startswith("/System/Library/Frameworks/CFNetwork.framework")
            ).base_address
        except StopIteration:
            raise MissingLibraryError from None

    @cached_async_method
    async def _arm_enable_har_global(self) -> DarwinSymbolT_co:
        """
        In order to find an unexported global variable, we use a sequence of instructions that we know comes after
        the aforementioned variable is accessed.

            88 07 2D D0                 ADRP            X8, #har_global@PAGE
            08 41 55 39                 LDRB            W8, [X8,#har_global@PAGEOFF]
            08 03 00 34                 CBZ             W8, loc_187DA1294
            E0 03 13 AA                 MOV             X0, X19 ; __str
            01 00 80 D2                 MOV             X1, #0  ; __endptr
            42 01 80 52                 MOV             W2, #0xA ; __base

        After getting the address of the instruction `mov x0,x19`, we need to rewind 2 instructions. Next, we verify
        that the above 2 instructions are `adrp` && `ldrb` . Then, extract the page address + page offset and
        calculate the affective address.
        """

        address = []
        regex_hex = r"0x[0-9a-fA-F]+"
        start = await self._cfnetwork_base()
        while True:
            pattern_addr = await self._client.symbols.memmem.z(start, 0xFFFFFFFF, ARM_PATTERN, len(ARM_PATTERN))
            if pattern_addr == 0:
                raise HarGlobalNotFoundError()
            pattern_sym = self._client.symbol(pattern_addr)
            disass = await (pattern_sym - len(ARM_PATTERN)).disass.z(8)
            if disass[0].mnemonic == "adrp" and disass[1].mnemonic == "ldrb":
                break
            # search next occurrence
            start = pattern_addr + 1

        for instruction in disass:
            address.append(int(re.findall(regex_hex, instruction.op_str)[0], 16))
        return self._client.symbol(sum(address))

    @cached_async_method
    async def _intel_enable_har_global(self) -> DarwinSymbolT_co:
        """
        In order to find an unexported global variable, we use a sequence of instructions that we know comes before
        the aforementioned variable is accessed.

            48 89 DF                    mov     rdi, rbx        ; __str
            31 F6                       xor     esi, esi        ; __endptr
            BA 0A 00 00                 mov     edx, 0Ah        ; __base
            00
            E8 78 EE 10                 call    _strtol
            00
            48 89 C3                    mov     rbx, rax
            88 1D 19 9C                 mov     cs:har_global_0, bl  <-----------------
        """
        op_str_pattern = "byte ptr [rip +"
        start = await self._cfnetwork_base()
        while True:
            pattern_addr = await self._client.symbols.memmem.z(start, 0xFFFFFFFF, INTEL_PATTERN, len(INTEL_PATTERN))
            if pattern_addr == 0:
                raise HarGlobalNotFoundError()
            pattern_sym = self._client.symbol(pattern_addr)
            disass = await (pattern_sym + len(INTEL_PATTERN)).disass.z(100)
            if (
                disass[0].mnemonic == "call"
                and disass[1].mnemonic == "mov"
                and disass[2].mnemonic == "mov"
                and disass[2].op_str.startswith(op_str_pattern)
            ):
                offset = int(disass[2].op_str.split(op_str_pattern, 1)[1].split("]")[0], 0)
                return self._client.symbol(disass[2].address + offset)
            start = pattern_addr + 1

    @cached_async_method
    async def _enable_har_global(self) -> DarwinSymbolT_co:
        if (await self._client.get_uname.z()).machine == "x86_64":
            return await self._intel_enable_har_global()
        return await self._arm_enable_har_global()

    @zyncio.zmethod
    async def install_cfnetwork_diagnostics_profile(self) -> None:
        await self._client.preferences.cf.set.z(
            "AppleCFNetworkDiagnosticLogging", 3, GLOBAL_DOMAIN, username="kCFPreferencesAnyUser"
        )

    @zyncio.zmethod
    async def remove_cfnetwork_diagnostics_profile(self) -> None:
        await self._client.preferences.cf.remove.z(
            "AppleCFNetworkDiagnosticLogging", GLOBAL_DOMAIN, username="kCFPreferencesAnyUser"
        )

    @zyncio.zmethod
    async def set_harlogger_for_process(self, value: bool, pid: int) -> None:
        process = await self._client.processes.get_by_pid.z(pid)
        await self._set_harlogger_for_process(value, process)
        await self.set_har_capture_global.z(True)

    @zyncio.zmethod
    async def set_harlogger_for_all(self, value: bool, expression: str | None = None) -> None:
        for p in await self._client.processes.list.z():
            if p.pid == 0:
                continue
            if expression and expression not in (await type(p).basename(p) or ""):
                continue
            try:
                await self._set_harlogger_for_process(value, p)
                logger.info(f"{'Enabled' if value else 'Disabled'} for {await type(p).basename(p)}")
            except BadReturnValueError:
                logger.exception(f"Failed To enable for {p}")
        await self.set_har_capture_global.z(True)

    @zyncio.zmethod
    async def set_unredacted_logs(self, enable: bool = True) -> None:
        """
        enable/disable unredacted logs (allows seeing the <private> strings)
        https://github.com/EthanArbuckle/unredact-private-os_logs
        """
        async with await self._client.preferences.sc.open.z(
            "/Library/Preferences/Logging/com.apple.system.logging.plist"
        ) as pref:
            await pref.set_dict.z({"Enable-Logging": True, "Enable-Private-Data": enable})
        await (await self._client.processes.get_by_basename.z("logd")).kill.z(SIGKILL)

    @zyncio.zmethod
    async def set_har_capture_global(self, enable: bool = True) -> None:
        """
        enable/disable HAR logging
        https://github.com/doronz88/harlogger
        """
        users = ["mobile", "root"]
        if enable:
            for user in users:
                # settings copied from DiagnosticExtension.appex
                await self._client.preferences.cf.set.z(
                    "har-capture-global",
                    datetime.datetime(9999, 12, 31, 23, 59, 59),
                    "com.apple.CFNetwork",
                    user,
                    hostname=kCFPreferencesAnyHost,
                )
                await self._client.preferences.cf.set.z(
                    "har-body-size-limit", 0x100000, "com.apple.CFNetwork", user, hostname=kCFPreferencesAnyHost
                )
                subsystem = await (await type(self).preferences_manager(self)).get_subsystem.z("com.apple.CFNetwork")
                category = await subsystem.get_category.z("HAR")

                await type(category).enabled_level.fset(category, OsLogLevel.DEFAULT)
                await type(category).persisted_level.fset(category, OsLogLevel.DEFAULT)
        else:
            for user in users:
                await self._client.preferences.cf.set.z(
                    "har-capture-global",
                    datetime.datetime(1970, 1, 1, 1, 1, 1),
                    "com.apple.CFNetwork",
                    user,
                    hostname=kCFPreferencesAnyHost,
                )

        if await self._client.symbols.notify_post.z("com.apple.CFNetwork.har-capture-update"):
            raise BadReturnValueError("notify_post() failed")

    async def _set_harlogger_for_process(self, value: bool, process: Process) -> None:
        await process.poke.z(await self._enable_har_global(), value.to_bytes(1, "little"))
