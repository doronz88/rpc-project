import sqlite3

from rpcclient.core.structs.consts import SIGKILL
from rpcclient.core.subsystems.network import Network

PINNING_RULED_DB = '/private/var/protected/trustd/pinningrules.sqlite3'
SYSTEM_CONFIGURATION_PLIST = '/private/var/Managed Preferences/mobile/com.apple.SystemConfiguration.plist'


class DarwinNetwork(Network):
    """" Network utils """

    def __init__(self, client):
        super().__init__(client)

    @property
    def proxy_settings(self) -> dict:
        return self._client.symbols.CFNetworkCopySystemProxySettings().py()

    def set_http_proxy(self, ip: str, port: int) -> None:
        with self._client.preferences.sc.open(SYSTEM_CONFIGURATION_PLIST) as config:
            config.set('Proxies', {'HTTPProxyType': 1,
                                   'HTTPEnable': 1,
                                   'HTTPPort': port,
                                   'HTTPSProxy': ip,
                                   'HTTPSPort': port,
                                   'HTTPProxy': ip,
                                   'HTTPSEnable': 1,
                                   'BypassAllowed': 0})
        self._client.processes.get_by_basename('configd').kill(SIGKILL)

    def remove_http_proxy(self) -> None:
        with self._client.preferences.sc.open(SYSTEM_CONFIGURATION_PLIST) as config:
            config.remove('Proxies')
        self._client.processes.get_by_basename('configd').kill(SIGKILL)

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
