import typing

from rpcclient.exceptions import RpcClientException

kCFPreferencesCurrentUser = 'kCFPreferencesCurrentUser'
kCFPreferencesAnyUser = 'kCFPreferencesAnyUser'
kCFPreferencesCurrentHost = 'kCFPreferencesCurrentHost'
kCFPreferencesAnyHost = 'kCFPreferencesAnyHost'


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

    def copy_key_list(self, application_id: str, username: str = kCFPreferencesCurrentUser,
                      hostname: str = kCFPreferencesCurrentHost) -> typing.Optional[typing.List[str]]:
        application_id = self._client.cf(application_id)
        username = self._client.cf(username)
        hostname = self._client.cf(hostname)
        return self._client.symbols.CFPreferencesCopyKeyList(application_id, username, hostname).py

    def copy_value(self, key: str, application_id: str, username: str = kCFPreferencesCurrentUser,
                   hostname: str = kCFPreferencesCurrentHost) -> typing.Optional[str]:
        key = self._client.cf(key)
        application_id = self._client.cf(application_id)
        username = self._client.cf(username)
        hostname = self._client.cf(hostname)
        return self._client.symbols.CFPreferencesCopyValue(key, application_id, username, hostname).py

    def copy_all_values(self, application_id: str, username: str = kCFPreferencesCurrentUser,
                        hostname: str = kCFPreferencesCurrentHost) -> typing.Optional[typing.Mapping]:
        result = {}
        key_list = self.copy_key_list(application_id, username, hostname)
        if not key_list:
            raise RpcClientException(f'failed to get key list for: {application_id}/{username}/{hostname}')
        for k in key_list:
            result[k] = self.copy_value(k, application_id, username, hostname)
        return result

    def set_value(self, key: str, value: str, application_id: str, username: str = kCFPreferencesCurrentUser,
                  hostname: str = kCFPreferencesCurrentHost):
        key = self._client.cf(key)
        value = self._client.cf(value)
        application_id = self._client.cf(application_id)
        username = self._client.cf(username)
        hostname = self._client.cf(hostname)
        self._client.symbols.CFPreferencesSetValue(key, value, application_id, username, hostname)
