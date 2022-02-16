import typing

from rpcclient.exceptions import RpcClientException


class SCPreferencesObject:
    def __init__(self, client, ref):
        self._client = client
        self._ref = ref

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            yield
        finally:
            self.release()

    @property
    def keys(self) -> typing.List[str]:
        return self._client.symbols.SCPreferencesCopyKeyList(self._ref).py

    def set(self, key: str, value):
        if not self._client.symbols.SCPreferencesSetValue(self._ref, self._client.cf(key), self._client.cf(value)):
            raise RpcClientException(f'SCPreferencesSetValue failed to set: {key}')
        self._commit()

    def remove(self, key: str):
        if not self._client.symbols.SCPreferencesRemoveValue(self._ref, self._client.cf(key)):
            raise RpcClientException(f'SCPreferencesRemoveValue failed to remove: {key}')
        self._commit()

    def get(self, key: str):
        return self._client.symbols.SCPreferencesGetValue(self._ref, self._client.cf(key)).py

    def to_dict(self) -> typing.Mapping:
        result = {}
        for k in self.keys:
            result[k] = self.get(k)
        return result

    def release(self):
        self._client.CFRelase(self._ref)

    def _commit(self):
        if not self._client.symbols.SCPreferencesCommitChanges(self._ref):
            raise RpcClientException('SCPreferencesCommitChanges failed')
        self._client.symbols.SCPreferencesSynchronize(self._ref)


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

    def get_preferences_object(self, preferences_id: str) -> SCPreferencesObject:
        ref = self._client.symbols.SCPreferencesCreate(0, self._client.cf('rpcserver'), self._client.cf(preferences_id))
        if not ref:
            raise RpcClientException(f'SCPreferencesCreate failed for: {preferences_id}')
        return SCPreferencesObject(self._client, ref)

    def get_key_list(self, preferences_id: str) -> typing.List[str]:
        with self.get_preferences_object(preferences_id) as o:
            return o.keys

    def get_dict(self, preferences_id: str):
        with self.get_preferences_object(preferences_id) as o:
            return o.to_dict()
