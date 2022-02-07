import typing

kCFPreferencesCurrentUser = 'kCFPreferencesCurrentUser'
kCFPreferencesAnyUser = 'kCFPreferencesAnyUser'
kCFPreferencesCurrentHost = 'kCFPreferencesCurrentHost'
kCFPreferencesAnyHost = 'kCFPreferencesAnyHost'


class Preferences:
    def __init__(self, client):
        """
        :param rpcclient.client.darwin_client.DarwinClient client:
        """
        self._client = client

    def copy_key_list(self, application_id: str, username: str = kCFPreferencesCurrentUser,
                      hostname: str = kCFPreferencesCurrentHost) -> typing.Optional[typing.List[str]]:
        application_id = self._client.cfstr(application_id)
        username = self._client.cfstr(username)
        hostname = self._client.cfstr(hostname)
        return self._client.symbols.CFPreferencesCopyKeyList(application_id, username, hostname).py

    def copy_value(self, key: str, application_id: str, username: str = kCFPreferencesCurrentUser,
                   hostname: str = kCFPreferencesCurrentHost) -> typing.Optional[str]:
        key = self._client.cfstr(key)
        application_id = self._client.cfstr(application_id)
        username = self._client.cfstr(username)
        hostname = self._client.cfstr(hostname)
        return self._client.symbols.CFPreferencesCopyValue(key, application_id, username, hostname).py

    def copy_all_values(self, application_id: str, username: str = kCFPreferencesCurrentUser,
                        hostname: str = kCFPreferencesCurrentHost) -> typing.Optional[typing.Mapping]:
        result = {}
        for k in self.copy_key_list(application_id, username, hostname):
            result[k] = self.copy_value(k, application_id, username, hostname)
        return result

    def set_value(self, key: str, value: str, application_id: str, username: str = kCFPreferencesCurrentUser,
                  hostname: str = kCFPreferencesCurrentHost):
        key = self._client.cfstr(key)
        value = self._client.cfstr(value)
        application_id = self._client.cfstr(application_id)
        username = self._client.cfstr(username)
        hostname = self._client.cfstr(hostname)
        self._client.symbols.CFPreferencesSetValue(key, value, application_id, username, hostname)
