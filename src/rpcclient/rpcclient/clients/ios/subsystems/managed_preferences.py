import plistlib
import uuid
from collections.abc import Mapping
from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.common import CfSerializable
from rpcclient.clients.darwin.consts import kCFAllocatorDefault
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import BadReturnValueError, RpcClientException, RpcFileNotFoundError


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient

MANAGED_PREFERENCES_ROOT = "/Library/Managed Preferences"
DEFAULT_PROFILE_PREFIX = "com.rpcclient.managed"
MCX_PAYLOAD_TYPE = "com.apple.ManagedClient.preferences"
RESTRICTIONS_PAYLOAD_TYPE = "com.apple.applicationaccess"


class _MCBase(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """shared MCProfileConnection plumbing (iOS ManagedConfiguration)"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client

    async def _shared_connection(self):
        await self._client.load_framework("ManagedConfiguration")
        cls = await self._client.symbols.objc_getClass("MCProfileConnection")
        if not cls:
            raise RpcClientException("MCProfileConnection is unavailable (ManagedConfiguration failed to load)")
        return await cls.objc_call("sharedConnection")

    async def _raise_on_mc_error(self, p_error, what: str) -> None:
        err = await p_error.getindex(0)
        if not err:
            return
        reason = await (await self._client.objc_symbol(err).objc_call("localizedDescription")).py()
        raise BadReturnValueError(f"{what} failed: {reason}")


class ManagedProfile(_MCBase[DarwinSymbolT_co], Generic[DarwinSymbolT_co]):
    """
    The MDM Managed Preferences store (``com.apple.ManagedClient.preferences``), plus the raw
    configuration-profile primitives that deliver it.

    Reads of the *effective* value come off the plists under
    ``/Library/Managed Preferences[/<user>]/<application_id>.plist``. Writes install/remove a
    profile through profiled (``-[MCProfileConnection installProfileData:outError:]`` /
    ``removeProfileWithIdentifier:``) - the store is never poked directly.
    """

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]", user: str = "mobile") -> None:
        super().__init__(client)
        self._user = user

    # -- managed preferences (per-domain) ------------------------------------

    def path(self, application_id: str) -> str:
        """absolute path of the effective managed plist backing a given domain"""
        root = MANAGED_PREFERENCES_ROOT
        if self._user:
            root = f"{root}/{self._user}"
        return f"{root}/{application_id}.plist"

    def default_identifier(self, application_id: str) -> str:
        """the profile identifier ``set`` / ``set_dict`` use for a given domain"""
        return f"{DEFAULT_PROFILE_PREFIX}.{application_id}"

    async def get_dict(self, application_id: str) -> dict:
        """read the effective managed domain (empty dict if nothing is managed)"""
        try:
            buf = await self._client.fs.read_file(self.path(application_id))
        except RpcFileNotFoundError:
            return {}
        return plistlib.loads(buf) if buf else {}

    async def get_keys(self, application_id: str) -> list[str]:
        """list the managed keys of a given domain"""
        return list((await self.get_dict(application_id)).keys())

    async def get_value(self, key: str, application_id: str) -> CfSerializable:
        """read a single managed value (None if the key isn't managed)"""
        return (await self.get_dict(application_id)).get(key)

    async def set(self, key: str, value: CfSerializable, application_id: str, *, identifier: str | None = None) -> str:
        """force a single managed value (merged over the current view). returns the profile identifier"""
        forced = await self.get_dict(application_id)
        forced[key] = value
        return await self.set_dict(forced, application_id, identifier=identifier)

    async def set_dict(self, d: Mapping, application_id: str, *, identifier: str | None = None) -> str:
        """force an entire managed domain by installing an MCX profile. returns the profile identifier"""
        identifier = identifier or self.default_identifier(application_id)
        profile = self._build_mcx_profile(application_id, dict(d), identifier)
        await self.install(plistlib.dumps(profile, fmt=plistlib.FMT_XML))
        return identifier

    async def clear(self, application_id: str, *, identifier: str | None = None) -> None:
        """remove the managed profile backing a domain"""
        await self.remove(identifier or self.default_identifier(application_id))

    # -- raw configuration profiles ------------------------------------------

    async def install(self, profile_data: bytes) -> None:
        """install a full configuration profile via ``-[MCProfileConnection installProfileData:outError:]``"""
        connection = await self._shared_connection()
        data = await self._client.symbols.CFDataCreate(kCFAllocatorDefault, profile_data, len(profile_data))
        async with self._client.safe_malloc(8) as p_error:
            await p_error.setindex(0, 0)
            await connection.objc_call("installProfileData:outError:", data, p_error)
            await self._raise_on_mc_error(p_error, "installProfileData")

    async def remove(self, identifier: str) -> None:
        """remove an installed profile via ``-[MCProfileConnection removeProfileWithIdentifier:]``"""
        connection = await self._shared_connection()
        await connection.objc_call("removeProfileWithIdentifier:", await self._client.cf(identifier))

    async def is_installed(self, identifier: str) -> bool:
        """query ``-[MCProfileConnection isProfileInstalledWithIdentifier:outError:]``"""
        connection = await self._shared_connection()
        async with self._client.safe_malloc(8) as p_error:
            await p_error.setindex(0, 0)
            result = await connection.objc_call(
                "isProfileInstalledWithIdentifier:outError:", await self._client.cf(identifier), p_error
            )
            await self._raise_on_mc_error(p_error, "isProfileInstalledWithIdentifier")
        return bool(result)

    async def get_data(self, identifier: str) -> bytes | None:
        """raw plist of an installed profile (``-[MCProfileConnection installedProfileDataWithIdentifier:]``)"""
        connection = await self._shared_connection()
        data = await connection.objc_call("installedProfileDataWithIdentifier:", await self._client.cf(identifier))
        if not data:
            return None
        length = await data.objc_call("length")
        if not length:
            return b""
        return await (await data.objc_call("bytes")).peek(length)

    async def get(self, identifier: str) -> dict | None:
        """read back an installed profile through profiled and parse it (None if absent).

        Returns what the profile *declares* - not the effective merged value (that is ``get_dict``).
        Signed profiles are CMS-wrapped and won't parse.
        """
        data = await self.get_data(identifier)
        if not data:
            return None
        return plistlib.loads(data)

    def _build_mcx_profile(self, application_id: str, settings: dict, identifier: str) -> dict:
        return {
            "PayloadType": "Configuration",
            "PayloadVersion": 1,
            "PayloadIdentifier": identifier,
            "PayloadUUID": str(uuid.uuid4()).upper(),
            "PayloadDisplayName": f"Managed {application_id}",
            "PayloadContent": [
                {
                    "PayloadType": MCX_PAYLOAD_TYPE,
                    "PayloadVersion": 1,
                    "PayloadIdentifier": f"{identifier}.{application_id}",
                    "PayloadUUID": str(uuid.uuid4()).upper(),
                    "PayloadContent": {
                        application_id: {"Forced": [{"mcx_preference_settings": settings}]},
                    },
                }
            ],
        }


class ManagedRestrictions(_MCBase[DarwinSymbolT_co], Generic[DarwinSymbolT_co]):
    """
    MDM restrictions / MCFeature settings (the ``com.apple.applicationaccess`` namespace).

    These are NOT plist keys: the effective value is a merge of the built-in default and the
    restrictions contributed by installed profiles/clients. This is the store behind accessors
    like ``DiagnosticLogSubmissionEnabled()`` (``allowDiagnosticSubmission``).

    Set them either directly through ``MCProfileConnection`` (``set_bool`` / ``set_parameters``)
    or by installing a Restrictions profile (``install`` / ``remove``).
    """

    async def effective_bool(self, setting: str) -> bool:
        """``-[MCProfileConnection effectiveBoolValueForSetting:]`` (merged default + restrictions)"""
        connection = await self._shared_connection()
        return bool(await connection.objc_call("effectiveBoolValueForSetting:", await self._client.cf(setting)))

    async def default_bool(self, setting: str) -> bool:
        """built-in default (``-[MCProfileConnection defaultBoolValueForSetting:]``)"""
        connection = await self._shared_connection()
        return bool(await connection.objc_call("defaultBoolValueForSetting:", await self._client.cf(setting)))

    async def effective_value(self, setting: str) -> CfSerializable:
        """``-[MCProfileConnection effectiveValueForSetting:]`` for non-boolean settings"""
        connection = await self._shared_connection()
        result = await connection.objc_call("effectiveValueForSetting:", await self._client.cf(setting))
        if not result:
            return None
        return await result.py()

    async def effective_parameters(self, setting: str) -> dict | None:
        """the effective parameters dict (``-[MCProfileConnection effectiveParametersForBoolSetting:]``).

        Use this to discover the parameters shape, tweak it, and hand it back to ``set_parameters``.
        """
        connection = await self._shared_connection()
        result = await connection.objc_call("effectiveParametersForBoolSetting:", await self._client.cf(setting))
        if not result:
            return None
        return await result.py(dict)

    async def default_parameters(self, setting: str) -> dict | None:
        """the built-in default parameters dict (``-[MCProfileConnection defaultParametersForBoolSetting:]``)"""
        connection = await self._shared_connection()
        result = await connection.objc_call("defaultParametersForBoolSetting:", await self._client.cf(setting))
        if not result:
            return None
        return await result.py(dict)

    async def effective_restrictions(self) -> dict:
        """the whole effective restrictions map - every setting at once
        (``-[MCProfileConnection effectiveRestrictions]``).

        This is the bulk view (setting -> value); ``effective_parameters(setting)`` is the
        per-setting metadata for one key. There is no bulk-default equivalent - defaults are
        exposed per-setting only (``default_bool`` / ``default_parameters``).
        """
        connection = await self._shared_connection()
        result = await connection.objc_call("effectiveRestrictions")
        if not result:
            return {}
        return await result.py(dict)

    async def user_restrictions(self) -> dict:
        """the whole user-set restrictions map (``-[MCProfileConnection userSettings]``)"""
        connection = await self._shared_connection()
        result = await connection.objc_call("userSettings")
        if not result:
            return {}
        return await result.py(dict)

    async def set_bool(self, setting: str, value: bool) -> None:
        """set a boolean restriction directly (``-[MCProfileConnection setBoolValue:forSetting:]``).

        No profile install. Protected settings may need the richer
        ``setBoolValue:ask:forSetting:configurationUUID:toSystem:user:credentialSet:`` variants,
        which are not wrapped here.
        """
        connection = await self._shared_connection()
        await connection.objc_call("setBoolValue:forSetting:", value, await self._client.cf(setting))

    async def set_parameters(self, setting: str, parameters: Mapping, *, value_setting: bool = False) -> None:
        """set a restriction's full parameters (``-[MCProfileConnection setParameters:for{Bool,Value}Setting:]``).

        ``parameters`` is the same dict shape returned by ``default_parameters`` /
        ``effective_parameters`` - fetch one, modify it, pass it back.
        """
        selector = "setParameters:forValueSetting:" if value_setting else "setParameters:forBoolSetting:"
        connection = await self._shared_connection()
        await connection.objc_call(selector, await self._client.cf(dict(parameters)), await self._client.cf(setting))

    async def install(self, restrictions: Mapping, *, identifier: str | None = None) -> str:
        """impose restrictions by installing a ``com.apple.applicationaccess`` profile. returns the identifier.

        ``restrictions`` maps restriction keys to values, e.g. ``{"allowDiagnosticSubmission": False}``.
        Reinstalling the same ``identifier`` replaces the set; remove with ``remove``.
        """
        identifier = identifier or f"{DEFAULT_PROFILE_PREFIX}.restrictions"
        profile = self._build_restrictions_profile(dict(restrictions), identifier)
        await ManagedProfile(self._client).install(plistlib.dumps(profile, fmt=plistlib.FMT_XML))
        return identifier

    async def remove(self, *, identifier: str | None = None) -> None:
        """remove the restrictions profile installed by ``install``"""
        await ManagedProfile(self._client).remove(identifier or f"{DEFAULT_PROFILE_PREFIX}.restrictions")

    def _build_restrictions_profile(self, restrictions: dict, identifier: str) -> dict:
        return {
            "PayloadType": "Configuration",
            "PayloadVersion": 1,
            "PayloadIdentifier": identifier,
            "PayloadUUID": str(uuid.uuid4()).upper(),
            "PayloadDisplayName": "Restrictions",
            "PayloadContent": [
                {
                    "PayloadType": RESTRICTIONS_PAYLOAD_TYPE,
                    "PayloadVersion": 1,
                    "PayloadIdentifier": f"{identifier}.applicationaccess",
                    "PayloadUUID": str(uuid.uuid4()).upper(),
                    # Restrictions keys live directly in the payload dict (not wrapped in Forced)
                    **restrictions,
                }
            ],
        }


class ManagedPreferences(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    iOS MDM configuration, split by mechanism:

    - ``profile`` : the Managed Preferences store + raw configuration profiles.
    - ``restricted`` : the restrictions / MCFeature settings.

    iOS-only: everything goes through ``MCProfileConnection`` / ``ManagedConfiguration.framework``,
    which does not exist on macOS. Non-interactive install requires the calling process to be
    entitled for profiled access.
    """

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]", user: str = "mobile") -> None:
        self._client = client
        self.profile: ManagedProfile[DarwinSymbolT_co] = ManagedProfile(client, user)
        self.restricted: ManagedRestrictions[DarwinSymbolT_co] = ManagedRestrictions(client)
