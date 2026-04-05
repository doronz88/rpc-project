import platform
import plistlib
import posixpath
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.subsystems.scpreferences import SCPreference
from rpcclient.core._types import ClientBound


if TYPE_CHECKING:
    from rpcclient.clients.ios.client import BaseIosClient

PAIR_RECORD_PATH = "/var/root/Library/Lockdown/pair_records"
DATA_ARK_PATH = "/var/root/Library/Lockdown/data_ark.plist"
FAR_FUTURE_DATE = datetime(9999, 1, 1)


class PairRecord(ClientBound["BaseIosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Represents a Lockdown pairing record for a host."""

    def __init__(self, client: "BaseIosClient[DarwinSymbolT_co]", host_id: str) -> None:
        self._client = client
        self._host_id: str = host_id

    @property
    def host_id(self) -> str:
        """Return the host ID for this pairing record."""
        return self._host_id

    @zyncio.zproperty
    async def record(self) -> dict:
        """Return the raw pairing record plist as a dictionary."""
        return plistlib.loads(
            await self._client.fs.read_file.z(posixpath.join(PAIR_RECORD_PATH, f"{self._host_id}.plist"))
        )

    @zyncio.zproperty
    async def _date(self) -> datetime:
        """Return the pairing date for this host."""
        return (await type(self._client.lockdown).pair_dates(self._client.lockdown))[self._host_id]

    @_date.setter
    async def date(self, value: datetime) -> None:
        """Set the pairing date for this host."""
        await self._client.lockdown.set_pair_date.z(self._host_id, value)

    @zyncio.zproperty
    async def expiration_date(self) -> datetime:
        """Return the pairing expiration date (pairing date + 30 days)."""
        return await type(self).date(self) + timedelta(days=30)

    @zyncio.zmethod
    async def disable_expiration(self) -> None:
        """Disable expiration by setting the date far in the future."""
        await type(self).date.fset(self, FAR_FUTURE_DATE)

    def __repr__(self) -> str:
        exp_str = f" EXPIRATION:{self.expiration_date}" if zyncio.is_sync(self) else ""
        return f"<{self.__class__.__name__} HOST_ID:{self.host_id}{exp_str}>"


class Lockdown(ClientBound["BaseIosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Access and manage Lockdown pairing records and data ark."""

    def __init__(self, client: "BaseIosClient[DarwinSymbolT_co]") -> None:
        self._client = client

    @staticmethod
    def get_host_id(hostname: str | None = None) -> str:
        """Return the uppercase host ID for a hostname (default: local hostname)."""
        hostname = platform.node() if hostname is None else hostname
        host_id = uuid.uuid3(uuid.NAMESPACE_DNS, hostname)
        return str(host_id).upper()

    @zyncio.zproperty
    async def pair_records(self) -> list[PairRecord]:
        """Return the list of existing pairing records."""
        return [
            PairRecord(self._client, filename.split(".")[0])
            for filename in await self._client.fs.listdir.z(PAIR_RECORD_PATH)
        ]

    @zyncio.zproperty
    async def pair_dates(self) -> dict:
        """Return a mapping of host_id -> pairing date."""
        raw = await self._client.preferences.cf.get_dict.z("com.apple.mobile.ldpair", "mobile", "kCFPreferencesAnyHost")
        return {host_id: datetime.fromtimestamp(timestmap) for host_id, timestmap in raw.items()}

    @zyncio.zproperty
    async def data_ark(self) -> SCPreference[DarwinSymbolT_co]:
        """Return the data_ark plist as an SCPreference handle."""
        return await self._client.preferences.sc.open.z(DATA_ARK_PATH)

    @zyncio.zmethod
    async def set_pair_date(self, host_id: str, date: datetime) -> None:
        """Set the pairing date for a given host ID."""
        await self._client.preferences.cf.set.z(
            host_id, int(date.timestamp()), "com.apple.mobile.ldpair", "mobile", "kCFPreferencesAnyHost"
        )

    @zyncio.zmethod
    async def get_pair_record_by_host_id(self, host_id: str) -> PairRecord[DarwinSymbolT_co]:
        """Return the PairRecord for a specific host ID."""
        return PairRecord(self._client, host_id)

    @zyncio.zmethod
    async def get_pair_record_by_hostname(self, hostname: str) -> PairRecord[DarwinSymbolT_co]:
        """Return the PairRecord for a hostname."""
        return PairRecord(self._client, self.get_host_id(hostname))

    @zyncio.zmethod
    async def get_self_pair_record(self) -> PairRecord[DarwinSymbolT_co]:
        """Return the PairRecord for the current host."""
        return await self.get_pair_record_by_host_id.z(self.get_host_id())

    @zyncio.zmethod
    async def add_pair_record(self, pair_record: dict, date: datetime, hostname: str | None = None) -> None:
        """Add a new pairing record and set its pairing date."""
        pair_record = dict(pair_record)
        # remove private key from pair record before adding it
        pair_record.pop("HostPrivateKey")

        host_id = self.get_host_id(hostname)
        await self._client.fs.write_file.z(
            posixpath.join(PAIR_RECORD_PATH, f"{host_id}.plist"), plistlib.dumps(pair_record)
        )
        await self.set_pair_date.z(host_id, date)

    @zyncio.zmethod
    async def disable_expiration_for_all_existing_pair_records(self) -> None:
        """Disable expiration for all existing pairing records."""
        for record in await type(self).pair_records(self):
            record.disable_expiration()
