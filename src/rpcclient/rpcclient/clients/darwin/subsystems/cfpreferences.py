from contextlib import suppress
from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.common import CfSerializable, CfSerializableAny, CfSerializableT
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import BadReturnValueError, NoSuchPreferenceError, RpcClientException


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient

kCFPreferencesCurrentUser = "kCFPreferencesCurrentUser"
kCFPreferencesAnyUser = "kCFPreferencesAnyUser"
kCFPreferencesCurrentHost = "kCFPreferencesCurrentHost"
kCFPreferencesAnyHost = "kCFPreferencesAnyHost"
GLOBAL_DOMAIN = "Apple Global Domain"


class CFPreferences(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    API to the CFPreferences* functions - preferences managed by cfprefsd.
    https://developer.apple.com/documentation/corefoundation/preferences_utilities?language=objc
    """

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client

    @zyncio.zmethod
    async def get_keys(
        self, application_id: str, username: str = kCFPreferencesCurrentUser, hostname: str = kCFPreferencesCurrentHost
    ) -> list[str]:
        """wrapper for CFPreferencesCopyKeyList"""
        keys = await (
            await self._client.symbols.CFPreferencesCopyKeyList.z(
                await self._client.cf.z(application_id),
                await self._client.cf.z(username),
                await self._client.cf.z(hostname),
            )
        ).py.z()

        if keys is None:
            raise NoSuchPreferenceError()

        assert isinstance(keys, list)
        return keys

    @zyncio.zmethod
    async def get_value(
        self,
        key: str,
        application_id: str,
        username: str = kCFPreferencesCurrentUser,
        hostname: str = kCFPreferencesCurrentHost,
        typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = CfSerializableAny,
    ) -> CfSerializableT:
        """wrapper for CFPreferencesCopyValue"""
        value = await (
            await self._client.symbols.CFPreferencesCopyValue.z(
                await self._client.cf.z(key),
                await self._client.cf.z(application_id),
                await self._client.cf.z(username),
                await self._client.cf.z(hostname),
            )
        ).py.z(typ)

        return value

    @zyncio.zmethod
    async def get_dict(
        self, application_id: str, username: str = kCFPreferencesCurrentUser, hostname: str = kCFPreferencesCurrentHost
    ) -> dict:
        """get a dictionary representation of given preference"""
        key_list = await self.get_keys.z(application_id, username, hostname)
        if not key_list:
            raise RpcClientException(f"failed to get key list for: {application_id}/{username}/{hostname}")

        return {k: await self.get_value.z(k, application_id, username, hostname) for k in key_list}

    @zyncio.zmethod
    async def set(
        self,
        key: str,
        value: CfSerializable,
        application_id: str,
        username: str = kCFPreferencesCurrentUser,
        hostname: str = kCFPreferencesCurrentHost,
    ):
        """wrapper for CFPreferencesSetValue"""
        await self._client.symbols.CFPreferencesSetValue.z(
            await self._client.cf.z(key),
            await self._client.cf.z(value),
            await self._client.cf.z(application_id),
            await self._client.cf.z(username),
            await self._client.cf.z(hostname),
        )

    @zyncio.zmethod
    async def remove(
        self,
        key: str,
        application_id: str,
        username: str = kCFPreferencesCurrentUser,
        hostname: str = kCFPreferencesCurrentHost,
    ):
        """remove a given key from a preference"""
        await self._client.symbols.CFPreferencesSetValue.z(
            await self._client.cf.z(key),
            0,
            await self._client.cf.z(application_id),
            await self._client.cf.z(username),
            await self._client.cf.z(hostname),
        )

    @zyncio.zmethod
    async def set_dict(
        self,
        d: dict,
        application_id: str,
        username: str = kCFPreferencesCurrentUser,
        hostname: str = kCFPreferencesCurrentHost,
    ):
        """set entire preference dictionary (erase first if exists)"""
        with suppress(NoSuchPreferenceError):
            await self.clear.z(application_id, username, hostname)
        await self.update_dict.z(d, application_id, username, hostname)

    @zyncio.zmethod
    async def update_dict(
        self,
        d: dict,
        application_id: str,
        username: str = kCFPreferencesCurrentUser,
        hostname: str = kCFPreferencesCurrentHost,
    ):
        """update preference dictionary"""
        for k, v in d.items():
            await self.set.z(k, v, application_id, username, hostname)

    @zyncio.zmethod
    async def clear(
        self, application_id: str, username: str = kCFPreferencesCurrentUser, hostname: str = kCFPreferencesCurrentHost
    ):
        """remove all values from given preference"""
        for k in await self.get_keys.z(application_id, username, hostname):
            await self.remove.z(k, application_id, username, hostname)

    @zyncio.zmethod
    async def sync(
        self, application_id: str, username: str = kCFPreferencesCurrentUser, hostname: str = kCFPreferencesCurrentHost
    ):
        if not await self._client.symbols.CFPreferencesSynchronize.z(
            await self._client.cf.z(application_id),
            await self._client.cf.z(username),
            await self._client.cf.z(hostname),
        ):
            raise BadReturnValueError("CFPreferencesSynchronize() failed")
