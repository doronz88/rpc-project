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

    def flush_dns(self) -> None:
        self._client.processes.get_by_basename('mDNSResponder').kill(SIGKILL)
