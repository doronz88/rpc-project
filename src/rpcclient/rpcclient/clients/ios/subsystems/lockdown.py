import platform
import plistlib
import posixpath
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

from rpcclient.clients.darwin.subsystems.scpreferences import SCPreference

if TYPE_CHECKING:
    from rpcclient.clients.ios.client import IosClient

PAIR_RECORD_PATH = "/var/root/Library/Lockdown/pair_records"
DATA_ARK_PATH = "/var/root/Library/Lockdown/data_ark.plist"
FAR_FUTURE_DATE = datetime(9999, 1, 1)


class PairRecord:
    """Represents a Lockdown pairing record for a host."""

    def __init__(self, client: "IosClient", host_id: str) -> None:
        self._client = client
        self._host_id = host_id

    @property
    def host_id(self) -> str:
        """Return the host ID for this pairing record."""
        return self._host_id

    @property
    def record(self) -> dict:
        """Return the raw pairing record plist as a dictionary."""
        return plistlib.loads(self._client.fs.read_file(posixpath.join(PAIR_RECORD_PATH, f"{self._host_id}.plist")))

    @property
    def date(self) -> datetime:
        """Return the pairing date for this host."""
        return self._client.lockdown.pair_dates.get(self._host_id)

    @date.setter
    def date(self, value: datetime) -> None:
        """Set the pairing date for this host."""
        self._client.lockdown.set_pair_date(self._host_id, value)

    @property
    def expiration_date(self) -> datetime:
        """Return the pairing expiration date (pairing date + 30 days)."""
        return self.date + timedelta(days=30)

    def disable_expiration(self) -> None:
        """Disable expiration by setting the date far in the future."""
        self.date = FAR_FUTURE_DATE

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} HOST_ID:{self.host_id} EXPIRATION:{self.expiration_date}>"


class Lockdown:
    """Access and manage Lockdown pairing records and data ark."""

    def __init__(self, client: "IosClient") -> None:
        self._client = client

    @staticmethod
    def get_host_id(hostname: Optional[str] = None) -> str:
        """Return the uppercase host ID for a hostname (default: local hostname)."""
        hostname = platform.node() if hostname is None else hostname
        host_id = uuid.uuid3(uuid.NAMESPACE_DNS, hostname)
        return str(host_id).upper()

    @property
    def pair_records(self) -> list[PairRecord]:
        """Return the list of existing pairing records."""
        result = []
        for filename in self._client.fs.listdir(PAIR_RECORD_PATH):
            result.append(PairRecord(self._client, filename.split(".")[0]))
        return result

    @property
    def pair_dates(self) -> dict:
        """Return a mapping of host_id -> pairing date."""
        result = {}
        raw = self._client.preferences.cf.get_dict("com.apple.mobile.ldpair", "mobile", "kCFPreferencesAnyHost")
        for host_id, timestmap in raw.items():
            result[host_id] = datetime.fromtimestamp(timestmap)
        return result

    @property
    def data_ark(self) -> SCPreference:
        """Return the data_ark plist as an SCPreference handle."""
        return self._client.preferences.sc.open(DATA_ARK_PATH)

    def set_pair_date(self, host_id: str, date: datetime) -> None:
        """Set the pairing date for a given host ID."""
        self._client.preferences.cf.set(
            host_id, int(date.timestamp()), "com.apple.mobile.ldpair", "mobile", "kCFPreferencesAnyHost"
        )

    def get_pair_record_by_host_id(self, host_id: str) -> PairRecord:
        """Return the PairRecord for a specific host ID."""
        return PairRecord(self._client, host_id)

    def get_pair_record_by_hostname(self, hostname: str) -> PairRecord:
        """Return the PairRecord for a hostname."""
        return PairRecord(self._client, self.get_host_id(hostname))

    def get_self_pair_record(self) -> PairRecord:
        """Return the PairRecord for the current host."""
        return self.get_pair_record_by_host_id(self.get_host_id())

    def add_pair_record(self, pair_record: dict, date: datetime, hostname: Optional[str] = None) -> None:
        """Add a new pairing record and set its pairing date."""
        pair_record = dict(pair_record)
        # remove private key from pair record before adding it
        pair_record.pop("HostPrivateKey")

        host_id = self.get_host_id(hostname)
        self._client.fs.write_file(posixpath.join(PAIR_RECORD_PATH, f"{host_id}.plist"), plistlib.dumps(pair_record))
        self.set_pair_date(host_id, date)

    def disable_expiration_for_all_existing_pair_records(self) -> None:
        """Disable expiration for all existing pairing records."""
        for record in self.pair_records:
            record.disable_expiration()
