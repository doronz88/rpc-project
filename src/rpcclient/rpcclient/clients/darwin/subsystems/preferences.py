from typing import TYPE_CHECKING

from rpcclient.clients.darwin.subsystems.cfpreferences import CFPreferences
from rpcclient.clients.darwin.subsystems.scpreferences import SCPreferences

if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient


class Preferences:
    """Preferences utils"""

    def __init__(self, client: "DarwinClient"):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self.cf = CFPreferences(client)
        self.sc = SCPreferences(client)
