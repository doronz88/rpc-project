import sqlite3
from typing import Mapping

from rpcclient.network import Network
from rpcclient.structs.consts import SIGKILL

PINNING_RULED_DB = '/private/var/protected/trustd/pinningrules.sqlite3'


class DarwinNetwork(Network):
    """" Network utils """

    def __init__(self, client):
        super().__init__(client)

    @property
    def proxy_settings(self) -> Mapping:
        return self._client.symbols.CFNetworkCopySystemProxySettings().py()

    def remove_certificate_pinning(self) -> None:
        with self._client.fs.remote_file(PINNING_RULED_DB) as local_db_file:
            # truncate pinning rules
            conn = sqlite3.connect(local_db_file)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM rules')
            conn.commit()
            conn.close()

            # push new db
            self._client.fs.push(local_db_file, PINNING_RULED_DB)

            # restart trustd for changes to take affect
            self._client.processes.get_by_basename('trustd').kill(SIGKILL)

    def flush_dns(self) -> None:
        self._client.processes.get_by_basename('mDNSResponder').kill(SIGKILL)
