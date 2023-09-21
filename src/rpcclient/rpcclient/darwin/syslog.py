import datetime
import logging
import re
from typing import List

from cached_property import cached_property

from rpcclient.darwin.cfpreferences import GLOBAL_DOMAIN, kCFPreferencesAnyHost
from rpcclient.darwin.consts import OsLogLevel
from rpcclient.darwin.processes import Process
from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.exceptions import BadReturnValueError, HarGlobalNotFoundError, MissingLibraryError
from rpcclient.structs.consts import SIGKILL

MOV_RDI_RBX = b'\x48\x89\xdf'
XOR_ESI_ESI = b'\x31\xf6'
MOV_EDX_0A = b'\xba\x0a\x00\x00'
INTEL_PATTERN = MOV_RDI_RBX + XOR_ESI_ESI + MOV_EDX_0A + b'\x00'

MOV_X0_X9 = b'\xE0\x03\x13\xAA'
MOV_X1_0 = b'\x01\x00\x80\xD2'
MOV_W2_0XA = b'\x42\x01\x80\x52'
ARM_PATTERN = MOV_X0_X9 + MOV_X1_0 + MOV_W2_0XA

logger = logging.getLogger(__name__)


class OsLogPreferencesBase:
    def __init__(self, client, obj: DarwinSymbol):
        self._client = client
        self._object = obj

    @property
    def name(self) -> str:
        return self._object.objc_call('name').py()

    @property
    def persisted_level(self) -> OsLogLevel:
        return OsLogLevel(self._object.objc_call('persistedLevel'))

    @persisted_level.setter
    def persisted_level(self, value: OsLogLevel) -> None:
        self._object.objc_call('setPersistedLevel:', value)

    @property
    def default_persisted_level(self) -> OsLogLevel:
        return OsLogLevel(self._object.objc_call('defaultPersistedLevel'))

    @property
    def enabled_level(self) -> OsLogLevel:
        return OsLogLevel(self._object.objc_call('enabledLevel'))

    @enabled_level.setter
    def enabled_level(self, value: OsLogLevel) -> None:
        self._object.objc_call('setEnabledLevel:', value)

    @property
    def default_enabled_level(self) -> OsLogLevel:
        return OsLogLevel(self._object.objc_call('defaultEnabledLevel'))

    @property
    def _verbosity_description(self) -> str:
        return (f'ENABLED_LEVEL:{self.enabled_level.name}({self.enabled_level.value}) '
                f'PERSISTED_LEVEL:{self.persisted_level.name}({self.persisted_level.value})')

    def reset(self) -> None:
        self._object.objc_call('reset')

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} NAME:{self.name} {self._verbosity_description}>'


class OsLogPreferencesCategory(OsLogPreferencesBase):
    def __init__(self, client, category: str, subsystem: DarwinSymbol):
        obj = client.symbols.objc_getClass('OSLogPreferencesCategory').objc_call('alloc').objc_call(
            'initWithName:subsystem:', client.cf(category), subsystem)
        super().__init__(client, obj)

    @property
    def name(self) -> str:
        return self._object.objc_call('name').py()

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} NAME:{self.name} {self._verbosity_description}>'


class OsLogPreferencesSubsystem(OsLogPreferencesBase):
    def __init__(self, client, subsystem: str):
        obj = client.symbols.objc_getClass('OSLogPreferencesSubsystem').objc_call('alloc').objc_call(
            'initWithName:', client.cf(subsystem))
        super().__init__(client, obj)

    @property
    def category_strings(self) -> List[OsLogPreferencesCategory]:
        return self._object.objc_call('categories').py()

    @property
    def categories(self) -> List[OsLogPreferencesCategory]:
        result = []
        for name in self.category_strings:
            result.append(self.get_category(name))
        return result

    def get_category(self, name: str) -> OsLogPreferencesCategory:
        return OsLogPreferencesCategory(self._client, name, self._object)


class OsLogPreferencesManager(OsLogPreferencesBase):
    def __init__(self, client):
        obj = client.symbols.objc_getClass('OSLogPreferencesManager').objc_call('sharedManager')
        super().__init__(client, obj)

    @property
    def subsystem_strings(self) -> List[str]:
        return self._object.objc_call('subsystems').py()

    @property
    def subsystems(self) -> List[OsLogPreferencesSubsystem]:
        result = []
        for name in self.subsystem_strings:
            result.append(self.get_subsystem(name))
        return result

    def get_subsystem(self, name: str) -> OsLogPreferencesSubsystem:
        return OsLogPreferencesSubsystem(self._client, name)


class Syslog:
    """" manage syslog """

    def __init__(self, client):
        """
        @type client: rpcclient.darwin.client.DarwinClient
        """
        self._client = client
        self._load_logging_support_library()
        self.preferences_manager = OsLogPreferencesManager(self._client)

    @cached_property
    def _cfnetwork_base(self) -> int:
        self._client.load_framework('CFNetwork')
        cfnetwork = [image for image in self._client.images if
                     image.name.startswith('/System/Library/Frameworks/CFNetwork.framework')]
        if len(cfnetwork) < 1:
            raise MissingLibraryError()
        return cfnetwork[0].base_address

    @cached_property
    def _arm_enable_har_global(self) -> DarwinSymbol:
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
        regex_hex = r'0x[0-9a-fA-F]+'
        start = self._cfnetwork_base
        while True:
            pattern_addr = self._client.symbols.memmem(start, 0xffffffff, ARM_PATTERN, len(ARM_PATTERN))
            if pattern_addr == 0:
                raise HarGlobalNotFoundError()
            pattern_sym = self._client.symbol(pattern_addr)
            disass = (pattern_sym - len(ARM_PATTERN)).disass(8)
            if disass[0].mnemonic == 'adrp' and disass[1].mnemonic == 'ldrb':
                break
            # search next occurrence
            start = pattern_addr + 1

        for instruction in disass:
            address.append(
                int(re.findall(regex_hex, instruction.op_str)[0], 16)
            )
        return self._client.symbol(sum(address))

    @cached_property
    def _intel_enable_har_global(self) -> DarwinSymbol:
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
        op_str_pattern = 'byte ptr [rip +'
        start = self._cfnetwork_base
        while True:
            pattern_addr = self._client.symbols.memmem(start, 0xffffffff, INTEL_PATTERN, len(INTEL_PATTERN))
            if pattern_addr == 0:
                raise HarGlobalNotFoundError()
            pattern_sym = self._client.symbol(pattern_addr)
            disass = (pattern_sym + len(INTEL_PATTERN)).disass(100)
            if (disass[0].mnemonic == 'call' and disass[1].mnemonic == 'mov' and disass[2].mnemonic == 'mov' and
                    disass[2].op_str.startswith(op_str_pattern)):
                offset = int(disass[2].op_str.split(op_str_pattern, 1)[1].split(']')[0], 0)
                return self._client.symbol(disass[2].address + offset)
            start = pattern_addr + 1

    @cached_property
    def _enable_har_global(self) -> DarwinSymbol:
        if self._client.uname.machine == 'x86_64':
            return self._intel_enable_har_global
        return self._arm_enable_har_global

    def install_cfnetwork_diagnostics_profile(self) -> None:
        self._client.preferences.cf.set('AppleCFNetworkDiagnosticLogging', 3, GLOBAL_DOMAIN,
                                        username='kCFPreferencesAnyUser')

    def remove_cfnetwork_diagnostics_profile(self) -> None:
        self._client.preferences.cf.remove('AppleCFNetworkDiagnosticLogging', GLOBAL_DOMAIN,
                                           username='kCFPreferencesAnyUser')

    def set_harlogger_for_process(self, value: bool, pid: int) -> None:
        process = self._client.processes.get_by_pid(pid)
        self._set_harlogger_for_process(value, process)
        self.set_har_capture_global(True)

    def set_harlogger_for_all(self, value: bool, expression: str = None) -> None:
        for p in self._client.processes.list():
            if p.pid == 0:
                continue
            if expression and expression not in p.basename:
                continue
            try:
                self._set_harlogger_for_process(value, p)
                logger.info(f'{"Enabled" if value else "Disabled"} for {p.basename}')
            except BadReturnValueError:
                logger.error(f'Failed To enable for {p}')
        self.set_har_capture_global(True)

    def set_unredacted_logs(self, enable: bool = True):
        """
        enable/disable unredacted logs (allows seeing the <private> strings)
        https://github.com/EthanArbuckle/unredact-private-os_logs
        """
        with self._client.preferences.sc.open(
                '/Library/Preferences/Logging/com.apple.system.logging.plist') as pref:
            pref.set_dict({'Enable-Logging': True, 'Enable-Private-Data': enable})
        self._client.processes.get_by_basename('logd').kill(SIGKILL)

    def set_har_capture_global(self, enable: bool = True):
        """
        enable/disable HAR logging
        https://github.com/doronz88/harlogger
        """
        users = ['mobile', 'root']
        if enable:
            for user in users:
                # settings copied from DiagnosticExtension.appex
                self._client.preferences.cf.set('har-capture-global',
                                                datetime.datetime(9999, 12, 31, 23, 59, 59),
                                                'com.apple.CFNetwork', user, hostname=kCFPreferencesAnyHost)
                self._client.preferences.cf.set('har-body-size-limit',
                                                0x100000,
                                                'com.apple.CFNetwork', user, hostname=kCFPreferencesAnyHost)
                subsystem = self.preferences_manager.get_subsystem('com.apple.CFNetwork')
                category = subsystem.get_category('HAR')

                category.enabled_level = 2
                category.persisted_level = 2
        else:
            for user in users:
                self._client.preferences.cf.set('har-capture-global',
                                                datetime.datetime(1970, 1, 1, 1, 1, 1),
                                                'com.apple.CFNetwork', user, hostname=kCFPreferencesAnyHost)

        if self._client.symbols.notify_post('com.apple.CFNetwork.har-capture-update'):
            raise BadReturnValueError('notify_post() failed')

    def _load_logging_support_library(self) -> None:
        self._client.load_framework('LoggingSupport')

    def _set_harlogger_for_process(self, value: bool, process: Process) -> None:
        process.poke(self._enable_har_global, value.to_bytes(1, 'little'))
