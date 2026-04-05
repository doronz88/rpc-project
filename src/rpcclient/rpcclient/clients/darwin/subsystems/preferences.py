from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.subsystems.cfpreferences import CFPreferences
from rpcclient.clients.darwin.subsystems.scpreferences import SCPreferences
from rpcclient.core._types import ClientBound


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient


class Preferences(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Preferences utils"""

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self.cf: CFPreferences[DarwinSymbolT_co] = CFPreferences(client)
        self.sc: SCPreferences[DarwinSymbolT_co] = SCPreferences(client)
