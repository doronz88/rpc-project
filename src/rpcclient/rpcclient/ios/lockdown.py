import plistlib
from collections import namedtuple
from typing import List

PairRecord = namedtuple('PairRecord', 'system_buid hostname host_id certificate')


class Lockdown:
    def __init__(self, client):
        self._client = client

    @property
    def pair_records(self) -> List[PairRecord]:
        """ list pair records """
        result = []
        for entry in self._client.fs.scandir('/var/root/Library/Lockdown/pair_records'):
            with self._client.fs.open(entry.path, 'r') as f:
                record = plistlib.loads(f.read())
            result.append(PairRecord(system_buid=record['SystemBUID'], hostname=record.get('HostName'),
                                     host_id=record['HostID'], certificate=record['HostCertificate']))

        return result
