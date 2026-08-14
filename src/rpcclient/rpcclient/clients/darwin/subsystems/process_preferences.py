from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.common import CfSerializable
from rpcclient.clients.darwin.subsystems.cfpreferences import (
    kCFPreferencesAnyHost,
    kCFPreferencesAnyUser,
    kCFPreferencesCurrentUser,
)
from rpcclient.core._types import ClientBound


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient  # noqa: F401  (used in string annotation)
    from rpcclient.clients.darwin.subsystems.processes import Process


class ProcessPreferences(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Read/write a preference domain the way a *specific* process resolves it.

    With no ``application_id`` this targets the process's OWN bundle-identifier domain - i.e. what
    ``[NSUserDefaults standardUserDefaults]`` reads/writes for that process. (Note it is NOT
    ``kCFPreferencesCurrentApplication``: "current application" would be rpcserver, not the target.)

    Preference location is process-relative (container, uid), so a plain ``CFPreferencesCopyValue``
    from rpcserver would resolve in *rpcserver's* context. Instead this uses the container-scoped CF
    SPI - ``_CFPreferencesCopyValueWithContainer`` / ``_CFPreferencesSetValueWithContainer`` /
    ``_CFPreferencesCopyMultipleWithContainer`` - passing the *target's* container as a CFString path, so the
    request still goes through cfprefsd (correct merged/managed view, cache-coherent writes) but is
    resolved against the target's home.

    The container is the target's ``CFFIXED_USER_HOME`` (its data container) when it has one, else its
    uid's home (``/var/root`` for uid 0, otherwise ``/var/mobile``) - so a bare-domain daemon resolves
    correctly too. cfprefsd handles own/foreign/group resolution from there. iOS path layout.
    """

    def __init__(
        self, process: "Process[DarwinSymbolT_co]", application_id: str | None = None, *, any_user: bool = False
    ) -> None:
        self._client = process._client
        self._process = process
        self._id = application_id  # None -> resolved lazily to the process's own bundle id
        self._user = kCFPreferencesAnyUser if any_user else kCFPreferencesCurrentUser
        self._host = kCFPreferencesAnyHost

    async def application_id(self) -> str:
        """the resolved domain: the explicit id, or the process's own bundle id (``standardUserDefaults``)"""
        if self._id is None:
            self._id = await type(self._process).bundle_id(self._process) or await type(self._process).name(
                self._process
            )
        return self._id

    async def container(self) -> str:
        """the base directory the target resolves CurrentUser domains against.

        The target's data container (``CFFIXED_USER_HOME``) if sandboxed, else its ``HOME``
        (correct on macOS and iOS alike); falls back to the uid's iOS home if it has neither.
        """
        env = await type(self._process).environ(self._process)
        home = env.get("CFFIXED_USER_HOME") or env.get("HOME")
        if home:
            return home
        return "/var/root" if await type(self._process).uid(self._process) == 0 else "/var/mobile"

    async def _container_arg(self):
        # the *WithContainer SPI take the container as a CFString path (NOT a CFURL - a CFURL crashes)
        return await self._client.cf(await self.container())

    async def path(self) -> str:
        """the fully-resolved plist file this domain maps to for the target (CurrentUser / AnyHost)"""
        base = (
            "/Library/Preferences"
            if self._user == kCFPreferencesAnyUser
            else f"{await self.container()}/Library/Preferences"
        )
        return f"{base}/{await self.application_id()}.plist"

    async def get(self, key: str) -> CfSerializable:
        """read a single key as the target resolves it (``_CFPreferencesCopyValueWithContainer``)"""
        return await (
            await self._client.symbols._CFPreferencesCopyValueWithContainer(
                await self._client.cf(key),
                await self._client.cf(await self.application_id()),
                await self._client.cf(self._user),
                await self._client.cf(self._host),
                await self._container_arg(),
            )
        ).py()

    async def get_dict(self) -> dict:
        """the whole domain as the target resolves it (key list, then a value per key)"""
        # NOTE: don't use _CFPreferencesCopyMultipleWithContainer with keysToFetch=NULL - unlike the
        # public CopyMultiple it does not guard the NULL and crashes. Enumerate keys, then read each.
        return {key: await self.get(key) for key in await self.get_keys()}

    async def get_keys(self) -> list[str]:
        result = await self._client.symbols._CFPreferencesCopyKeyListWithContainer(
            await self._client.cf(await self.application_id()),
            await self._client.cf(self._user),
            await self._client.cf(self._host),
            await self._container_arg(),
        )
        if not result:
            return []
        return await result.py(list)

    async def set(self, key: str, value: CfSerializable) -> None:
        """set a single key (value=None removes), then sync"""
        container = await self._container_arg()
        await self._set_value(key, value, container)
        await self._sync(container)

    async def remove(self, key: str) -> None:
        await self.set(key, None)

    async def set_dict(self, d: dict) -> None:
        """replace the whole domain (removes keys not present in ``d``), then sync"""
        existing = set(await self.get_keys())
        container = await self._container_arg()
        for key in existing - set(d):
            await self._set_value(key, None, container)
        for key, value in d.items():
            await self._set_value(key, value, container)
        await self._sync(container)

    async def clear(self) -> None:
        await self.set_dict({})

    async def _set_value(self, key: str, value: CfSerializable, container) -> None:
        # value=None must be a NULL pointer to REMOVE the key; client.cf(None) is kCFNull, not NULL
        cf_value = 0 if value is None else await self._client.cf(value)
        await self._client.symbols._CFPreferencesSetValueWithContainer(
            await self._client.cf(key),
            cf_value,
            await self._client.cf(await self.application_id()),
            await self._client.cf(self._user),
            await self._client.cf(self._host),
            container,
        )

    async def _sync(self, container) -> None:
        await self._client.symbols._CFPreferencesSynchronizeWithContainer(
            await self._client.cf(await self.application_id()),
            await self._client.cf(self._user),
            await self._client.cf(self._host),
            container,
        )
