from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.subsystems.preferences import Preferences
from rpcclient.clients.ios.subsystems.managed_preferences import ManagedPreferences


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient


class IosPreferences(Preferences[DarwinSymbolT_co], Generic[DarwinSymbolT_co]):
    """Preferences utils - iOS also exposes the MDM managed store via ``managed``.

    ``managed`` is iOS-only: it goes through ``MCProfileConnection`` /
    ``ManagedConfiguration.framework``, which does not exist on macOS.
    """

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        super().__init__(client)
        self.managed: ManagedPreferences[DarwinSymbolT_co] = ManagedPreferences(client)
