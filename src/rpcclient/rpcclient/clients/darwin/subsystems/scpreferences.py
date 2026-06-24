from collections import UserDict
from collections.abc import Mapping
from typing import TYPE_CHECKING, Generic

import IPython
from pygments import formatters, highlight, lexers

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.common import CfSerializable
from rpcclient.clients.darwin.symbol import DarwinSymbol
from rpcclient.core._types import ClientBound
from rpcclient.core.allocated import Allocated
from rpcclient.exceptions import RpcClientException


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient

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


class SCPreference(Allocated["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]", preferences_id: str, ref) -> None:
        self._client = client
        self._ref = ref
        self._preferences_id: str = preferences_id

    async def keys(self) -> list[str]:
        """wrapper for SCPreferencesCopyKeyList"""
        return await (await self._client.symbols.SCPreferencesCopyKeyList(self._ref)).py(list)

    async def _set(self, key: str, value) -> None:
        """wrapper for SCPreferencesSetValue"""
        if not await self._client.symbols.SCPreferencesSetValue(
            self._ref,
            await self._client.cf(key),
            await self._client.cf(value),
        ):
            raise RpcClientException(f"SCPreferencesSetValue failed to set: {key}")

    async def set(self, key: str, value) -> None:
        """set key:value and commit the change"""
        await self._set(key, value)
        await self._commit()

    async def set_dict(self, d: Mapping) -> None:
        """set the entire preference dictionary (clear if already exists) and commit the change"""
        await self._clear()
        await self._update_dict(d)
        await self._commit()

    async def _update_dict(self, d: Mapping) -> None:
        """update preference dictionary"""
        for k, v in d.items():
            await self._set(k, v)

    async def update_dict(self, d: Mapping) -> None:
        """update preference dictionary and commit"""
        await self._update_dict(d)
        await self._commit()

    async def _remove(self, key: str) -> None:
        """wrapper for SCPreferencesRemoveValue"""
        if not await self._client.symbols.SCPreferencesRemoveValue(self._ref, await self._client.cf(key)):
            raise RpcClientException(f"SCPreferencesRemoveValue failed to remove: {key}")

    async def remove(self, key: str) -> None:
        """remove given key and commit"""
        await self._remove(key)
        await self._commit()

    async def get(self, key: str) -> CfSerializable:
        """wrapper for SCPreferencesGetValue"""
        return await (await self._client.symbols.SCPreferencesGetValue(self._ref, await self._client.cf(key))).py()

    async def get_dict(self) -> dict:
        """get a dictionary representation"""
        result = {}
        for k in await type(self).keys(self):
            result[k] = await self.get(k)
        return result

    async def interactive(self: "SCPreference[DarwinSymbol]") -> None:
        """open an interactive IPython shell for viewing and editing"""
        plist = await Plist.create(self)
        IPython.embed(  # pyright: ignore[reportAttributeAccessIssue]
            header=highlight(SHELL_USAGE, lexers.PythonLexer(), formatters.TerminalTrueColorFormatter(style="native")),
            user_ns={
                "d": plist,
            },
        )

    async def _clear(self) -> None:
        """clear dictionary"""
        for k in await type(self).keys(self):
            await self._remove(k)

    async def clear(self) -> None:
        """clear dictionary and commit"""
        await self._clear()
        await self._commit()

    async def _deallocate(self) -> None:
        """free the preference object"""
        await self._client.symbols.CFRelease(self._ref)

    async def _commit(self) -> None:
        """commit all changes"""
        if not await self._client.symbols.SCPreferencesCommitChanges(self._ref):
            raise RpcClientException("SCPreferencesCommitChanges failed")
        await self._client.symbols.SCPreferencesSynchronize(self._ref)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} NAME:{self._preferences_id}>"


class Plist(UserDict, Generic[DarwinSymbolT_co]):
    def __init__(self, preference: SCPreference[DarwinSymbolT_co], *, _dict: dict) -> None:
        super().__init__(_dict)
        self._preference = preference

    @staticmethod
    async def create(preference: SCPreference[DarwinSymbolT_co]) -> "Plist[DarwinSymbolT_co]":
        return Plist(preference, _dict=await preference.get_dict())

    async def commit(self) -> None:
        await self._preference.set_dict(self)


class SCPreferences(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    API to the SCPreferences* functions - preferences managed by SystemConfiguration framework.
    https://developer.apple.com/documentation/systemconfiguration/scpreferences?language=objc
    """

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client

    async def open(self, preferences_id: str) -> SCPreference[DarwinSymbolT_co]:
        """get an SCPreference from a given preferences_id"""
        ref = await self._client.symbols.SCPreferencesCreate(
            0, await self._client.cf("rpcserver"), await self._client.cf(preferences_id)
        )
        if not ref:
            raise RpcClientException(f"SCPreferencesCreate failed for: {preferences_id}")
        return SCPreference(self._client, preferences_id, ref)

    async def get_keys(self, preferences_id: str) -> list[str]:
        """get all keys from given preferences_id"""
        async with await self.open(preferences_id) as o:
            return await type(o).keys(o)

    async def get_dict(self, preferences_id: str) -> dict:
        """get dict from given preferences_id"""
        async with await self.open(preferences_id) as o:
            return await o.get_dict()
