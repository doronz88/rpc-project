import typing
from contextlib import suppress

from rpcclient.exceptions import BadReturnValueError, NoSuchPreferenceError, RpcClientException

kCFPreferencesCurrentUser = 'kCFPreferencesCurrentUser'
kCFPreferencesAnyUser = 'kCFPreferencesAnyUser'
kCFPreferencesCurrentHost = 'kCFPreferencesCurrentHost'
kCFPreferencesAnyHost = 'kCFPreferencesAnyHost'
GLOBAL_DOMAIN = 'Apple Global Domain'


class CFPreferences:
    """
    API to the CFPreferences* functions - preferences managed by cfprefsd.
    https://developer.apple.com/documentation/corefoundation/preferences_utilities?language=objc
    """

    def __init__(self, client):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client

    def get_keys(self, application_id: str, username: str = kCFPreferencesCurrentUser,
                 hostname: str = kCFPreferencesCurrentHost) -> typing.Optional[typing.List[str]]:
        """ wrapper for CFPreferencesCopyKeyList """
        application_id = self._client.cf(application_id)
        username = self._client.cf(username)
        hostname = self._client.cf(hostname)
        keys = self._client.symbols.CFPreferencesCopyKeyList(application_id, username, hostname).py()
        if keys is None:
            raise NoSuchPreferenceError()
        return keys

    def get_value(self, key: str, application_id: str, username: str = kCFPreferencesCurrentUser,
                  hostname: str = kCFPreferencesCurrentHost) -> typing.Optional[str]:
        """ wrapper for CFPreferencesCopyValue """
        key = self._client.cf(key)
        application_id = self._client.cf(application_id)
        username = self._client.cf(username)
        hostname = self._client.cf(hostname)
        return self._client.symbols.CFPreferencesCopyValue(key, application_id, username, hostname).py()

    def get_dict(self, application_id: str, username: str = kCFPreferencesCurrentUser,
                 hostname: str = kCFPreferencesCurrentHost) -> typing.Optional[typing.Mapping]:
        """ get a dictionary representation of given preference """
        result = {}
        key_list = self.get_keys(application_id, username, hostname)
        if not key_list:
            raise RpcClientException(f'failed to get key list for: {application_id}/{username}/{hostname}')
        for k in key_list:
            result[k] = self.get_value(k, application_id, username, hostname)
        return result

    def set(self, key: str, value, application_id: str, username: str = kCFPreferencesCurrentUser,
            hostname: str = kCFPreferencesCurrentHost):
        """ wrapper for CFPreferencesSetValue """
        self._client.symbols.CFPreferencesSetValue(self._client.cf(key), self._client.cf(value),
                                                   self._client.cf(application_id), self._client.cf(username),
                                                   self._client.cf(hostname))

    def remove(self, key: str, application_id: str, username: str = kCFPreferencesCurrentUser,
               hostname: str = kCFPreferencesCurrentHost):
        """ remove a given key from a preference """
        self._client.symbols.CFPreferencesSetValue(self._client.cf(key), 0,
                                                   self._client.cf(application_id), self._client.cf(username),
                                                   self._client.cf(hostname))

    def set_dict(self, d: typing.Mapping, application_id: str, username: str = kCFPreferencesCurrentUser,
                 hostname: str = kCFPreferencesCurrentHost):
        """ set entire preference dictionary (erase first if exists) """
        with suppress(NoSuchPreferenceError):
            self.clear(application_id, username, hostname)
        self.update_dict(d, application_id, username, hostname)

    def update_dict(self, d: typing.Mapping, application_id: str, username: str = kCFPreferencesCurrentUser,
                    hostname: str = kCFPreferencesCurrentHost):
        """ update preference dictionary """
        for k, v in d.items():
            self.set(k, v, application_id, username, hostname)

    def clear(self, application_id: str, username: str = kCFPreferencesCurrentUser,
              hostname: str = kCFPreferencesCurrentHost):
        """ remove all values from given preference """
        for k in self.get_keys(application_id, username, hostname):
            self.remove(k, application_id, username, hostname)

    def sync(self, application_id: str, username: str = kCFPreferencesCurrentUser,
             hostname: str = kCFPreferencesCurrentHost):
        if not self._client.symbols.CFPreferencesSynchronize(self._client.cf(application_id), self._client.cf(username),
                                                             self._client.cf(hostname)):
            raise BadReturnValueError('CFPreferencesSynchronize() failed')
