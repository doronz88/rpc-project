import logging

from rpcclient.core.subsystems.lief import Symbol
from rpcclient.exceptions import BadReturnValueError, RpcPermissionError

logger = logging.getLogger(__name__)


class Keychain:
    """ keychain utils """

    def __init__(self, client):
        self._client = client

    def add_internet_password(self, account: str, server: str, password: str):
        attributes = self._client.symbols.objc_getClass('NSMutableDictionary').objc_call('new')
        attributes.objc_call('setObject:forKey:', self._client.symbols.kSecClassInternetPassword[0],
                             self._client.symbols.kSecClass[0])
        attributes.objc_call('setObject:forKey:', self._client.cf(account), self._client.symbols.kSecAttrAccount[0])
        attributes.objc_call('setObject:forKey:', self._client.cf(server), self._client.symbols.kSecAttrServer[0])
        attributes.objc_call('setObject:forKey:', self._client.cf(password), self._client.symbols.kSecValueData[0])
        err = self._client.symbols.SecItemAdd(attributes, 0).c_int32
        if err != 0:
            raise BadReturnValueError(f'SecItemAdd() returned: {err}')

    def query_apple_share_passwords(self) -> list[dict]:
        return self._query(self._client.symbols.kSecClassAppleSharePassword)

    def query_internet_passwords(self) -> list[dict]:
        return self._query(self._client.symbols.kSecClassInternetPassword)

    def query_generic_passwords(self) -> list[dict]:
        return self._query(self._client.symbols.kSecClassGenericPassword)

    def query_identities(self) -> list[dict]:
        return self._query(self._client.symbols.kSecClassIdentity)

    def query_certificates(self) -> list[dict]:
        return self._query(self._client.symbols.kSecClassCertificate)

    def query_keys(self) -> list[dict]:
        return self._query(self._client.symbols.kSecClassKey)

    def _query(self, class_type: Symbol) -> list[dict]:
        with self._client.safe_malloc(8) as p_result:
            p_result[0] = 0

            query = self._client.symbols.objc_getClass('NSMutableDictionary').objc_call('new')
            query.objc_call('setObject:forKey:', class_type[0],
                            self._client.symbols.kSecClass[0])
            query.objc_call('setObject:forKey:', self._client.symbols.kSecMatchLimitAll[0],
                            self._client.symbols.kSecMatchLimit[0])
            query.objc_call('setObject:forKey:', self._client.symbols.kCFBooleanTrue[0],
                            self._client.symbols.kSecReturnAttributes[0])
            query.objc_call('setObject:forKey:', self._client.symbols.kCFBooleanTrue[0],
                            self._client.symbols.kSecReturnRef[0])
            query.objc_call('setObject:forKey:', self._client.symbols.kCFBooleanTrue[0],
                            self._client.symbols.kSecReturnData[0])

            err = self._client.symbols.SecItemCopyMatching(query, p_result).c_int32
            if err != 0:
                raise BadReturnValueError(f'SecItemCopyMatching() returned: {err}')

            result = p_result[0]

            if result == 0:
                raise RpcPermissionError()

            # results contain a reference which isn't plist-serializable
            keys_to_remove = [self._client.cf('v_Ref'), self._client.cf('accc')]
            for i in range(result.objc_call('count')):
                for removal_key in keys_to_remove:
                    result.objc_call('objectAtIndex:', i).objc_call('removeObjectForKey:', removal_key)
            return result.py()
