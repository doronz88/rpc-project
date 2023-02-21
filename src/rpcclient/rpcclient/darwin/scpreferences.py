import typing
from collections import UserDict

import IPython
from pygments import formatters, highlight, lexers

from rpcclient.allocated import Allocated
from rpcclient.exceptions import RpcClientException

SHELL_USAGE = """
# Welcome to SCPreference plist interactive editor!
# Please use the `d` global in order to make changes to the current plist.
# Use: `d.commit()` to save your changes when done.
#
# For example, consider the following:

# view current plist
print(d)

# modify an item
d['item1'] = 5

# update
d.commit()

# That's it! hope you had a pleasant ride! 👋
"""


class SCPreference(Allocated):
    def __init__(self, client, preferences_id: str, ref):
        super().__init__()
        self._client = client
        self._ref = ref
        self._preferences_id = preferences_id

    @property
    def keys(self) -> typing.List[str]:
        """ wrapper for SCPreferencesCopyKeyList """
        return self._client.symbols.SCPreferencesCopyKeyList(self._ref).py()

    def _set(self, key: str, value):
        """ wrapper for SCPreferencesSetValue """
        if not self._client.symbols.SCPreferencesSetValue(self._ref, self._client.cf(key), self._client.cf(value)):
            raise RpcClientException(f'SCPreferencesSetValue failed to set: {key}')

    def set(self, key: str, value):
        """ set key:value and commit the change """
        self._set(key, value)
        self._commit()

    def set_dict(self, d: typing.Mapping):
        """ set the entire preference dictionary (clear if already exists) and commit the change """
        self._clear()
        self._update_dict(d)
        self._commit()

    def _update_dict(self, d: typing.Mapping):
        """ update preference dictionary """
        for k, v in d.items():
            self._set(k, v)

    def update_dict(self, d: typing.Mapping):
        """ update preference dictionary and commit """
        self._update_dict(d)
        self._commit()

    def _remove(self, key: str):
        """ wrapper for SCPreferencesRemoveValue """
        if not self._client.symbols.SCPreferencesRemoveValue(self._ref, self._client.cf(key)):
            raise RpcClientException(f'SCPreferencesRemoveValue failed to remove: {key}')

    def remove(self, key: str):
        """ remove given key and commit """
        self._remove(key)
        self._commit()

    def get(self, key: str):
        """ wrapper for SCPreferencesGetValue """
        return self._client.symbols.SCPreferencesGetValue(self._ref, self._client.cf(key)).py()

    def get_dict(self) -> typing.Mapping:
        """ get a dictionary representation """
        result = {}
        for k in self.keys:
            result[k] = self.get(k)
        return result

    def interactive(self):
        """ open an interactive IPython shell for viewing and editing """
        plist = Plist(self)
        IPython.embed(
            header=highlight(SHELL_USAGE, lexers.PythonLexer(), formatters.TerminalTrueColorFormatter(style='native')),
            user_ns={
                'd': plist,
            })

    def _clear(self):
        """ clear dictionary """
        for k in self.keys:
            self._remove(k)

    def clear(self):
        """ clear dictionary and commit """
        self._clear()
        self._commit()

    def _deallocate(self):
        """ free the preference object """
        self._client.symbols.CFRelease(self._ref)

    def _commit(self):
        """ commit all changes """
        if not self._client.symbols.SCPreferencesCommitChanges(self._ref):
            raise RpcClientException('SCPreferencesCommitChanges failed')
        self._client.symbols.SCPreferencesSynchronize(self._ref)

    def __repr__(self):
        return f'<{self.__class__.__name__} NAME:{self._preferences_id}>'


class Plist(UserDict):
    def __init__(self, preference: SCPreference):
        super().__init__(preference.get_dict())
        self._preference = preference

    def commit(self):
        self._preference.set_dict(self)


class SCPreferences:
    """
    API to the SCPreferences* functions - preferences managed by SystemConfiguration framework.
    https://developer.apple.com/documentation/systemconfiguration/scpreferences?language=objc
    """

    def __init__(self, client):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client

    def open(self, preferences_id: str) -> SCPreference:
        """ get an SCPreference from a given preferences_id """
        ref = self._client.symbols.SCPreferencesCreate(0, self._client.cf('rpcserver'), self._client.cf(preferences_id))
        if not ref:
            raise RpcClientException(f'SCPreferencesCreate failed for: {preferences_id}')
        return SCPreference(self._client, preferences_id, ref)

    def get_keys(self, preferences_id: str) -> typing.List[str]:
        """ get all keys from given preferences_id """
        with self.open(preferences_id) as o:
            return o.keys

    def get_dict(self, preferences_id: str):
        """ get dict from given preferences_id """
        with self.open(preferences_id) as o:
            return o.get_dict()
