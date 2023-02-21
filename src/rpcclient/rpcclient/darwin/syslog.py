import datetime
from typing import List

from rpcclient.darwin.cfpreferences import kCFPreferencesAnyHost
from rpcclient.darwin.consts import OsLogLevel
from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.exceptions import BadReturnValueError
from rpcclient.structs.consts import SIGKILL


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
        return self._object.objc_call('setPersistedLevel:', value)

    @property
    def default_persisted_level(self) -> OsLogLevel:
        return OsLogLevel(self._object.objc_call('defaultPersistedLevel'))

    @property
    def enabled_level(self) -> OsLogLevel:
        return OsLogLevel(self._object.objc_call('enabledLevel'))

    @enabled_level.setter
    def enabled_level(self, value: OsLogLevel) -> None:
        return self._object.objc_call('setEnabledLevel:', value)

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
        return f'<{self.__class__.__name__} {self._verbosity_description}>'


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
        self._client = client
        self._load_logging_support_library()
        self.preferences_manager = OsLogPreferencesManager(self._client)

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
