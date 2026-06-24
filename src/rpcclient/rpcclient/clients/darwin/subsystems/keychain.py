import logging
from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT, DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import BadReturnValueError, RpcPermissionError


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient

logger = logging.getLogger(__name__)


class Keychain(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """keychain utils"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client

    async def add_internet_password(self, account: str, server: str, password: str) -> None:
        attributes = await (await self._client.symbols.objc_getClass("NSMutableDictionary")).objc_call("new")
        await attributes.objc_call(
            "setObject:forKey:",
            await self._client.symbols.kSecClassInternetPassword.getindex(0),
            await self._client.symbols.kSecClass.getindex(0),
        )
        await attributes.objc_call(
            "setObject:forKey:",
            await self._client.cf(account),
            await self._client.symbols.kSecAttrAccount.getindex(0),
        )
        await attributes.objc_call(
            "setObject:forKey:",
            await self._client.cf(server),
            await self._client.symbols.kSecAttrServer.getindex(0),
        )
        await attributes.objc_call(
            "setObject:forKey:",
            await self._client.cf(password),
            await self._client.symbols.kSecValueData.getindex(0),
        )
        err = (await self._client.symbols.SecItemAdd(attributes, 0)).c_int32
        if err != 0:
            raise BadReturnValueError(f"SecItemAdd() returned: {err}")

    async def query_apple_share_passwords(self) -> list[dict]:
        return await self._query(await self._client.symbols.kSecClassAppleSharePassword.resolve())

    async def query_internet_passwords(self) -> list[dict]:
        return await self._query(await self._client.symbols.kSecClassInternetPassword.resolve())

    async def query_generic_passwords(self) -> list[dict]:
        return await self._query(await self._client.symbols.kSecClassGenericPassword.resolve())

    async def query_identities(self) -> list[dict]:
        return await self._query(await self._client.symbols.kSecClassIdentity.resolve())

    async def query_certificates(self) -> list[dict]:
        return await self._query(await self._client.symbols.kSecClassCertificate.resolve())

    async def query_keys(self) -> list[dict]:
        return await self._query(await self._client.symbols.kSecClassKey.resolve())

    async def _query(self: "Keychain[DarwinSymbolT]", class_type: DarwinSymbolT) -> list[dict]:
        async with self._client.safe_malloc(8) as p_result:
            await p_result.setindex(0, 0)

            query = await (await self._client.symbols.objc_getClass("NSMutableDictionary")).objc_call("new")
            await query.objc_call(
                "setObject:forKey:", await class_type.getindex(0), await self._client.symbols.kSecClass.getindex(0)
            )
            await query.objc_call(
                "setObject:forKey:",
                await self._client.symbols.kSecMatchLimitAll.getindex(0),
                await self._client.symbols.kSecMatchLimit.getindex(0),
            )
            await query.objc_call(
                "setObject:forKey:",
                await self._client.symbols.kCFBooleanTrue.getindex(0),
                await self._client.symbols.kSecReturnAttributes.getindex(0),
            )
            await query.objc_call(
                "setObject:forKey:",
                await self._client.symbols.kCFBooleanTrue.getindex(0),
                await self._client.symbols.kSecReturnRef.getindex(0),
            )
            await query.objc_call(
                "setObject:forKey:",
                await self._client.symbols.kCFBooleanTrue.getindex(0),
                await self._client.symbols.kSecReturnData.getindex(0),
            )

            err = (await self._client.symbols.SecItemCopyMatching(query, p_result)).c_int32
            if err != 0:
                raise BadReturnValueError(f"SecItemCopyMatching() returned: {err}")

            result = await p_result.getindex(0)

            if result == 0:
                raise RpcPermissionError()

            # results contain a reference which isn't plist-serializable
            keys_to_remove = [await self._client.cf("v_Ref"), await self._client.cf("accc")]
            for i in range(await result.objc_call("count")):
                for removal_key in keys_to_remove:
                    await (await result.objc_call("objectAtIndex:", i)).objc_call("removeObjectForKey:", removal_key)
            return await result.py(list)
