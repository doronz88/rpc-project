import logging
from typing import TYPE_CHECKING

from rpcclient.exceptions import RpcSetDeveloperModeError

if TYPE_CHECKING:
    from rpcclient.clients.ios.client import IosClient

logger = logging.getLogger(__name__)


class Amfi:
    """AMFI utilities (AppleMobileFileIntegrity)."""

    def __init__(self, client: "IosClient") -> None:
        self._client = client
        self._client.load_framework("AppleMobileFileIntegrity")

    def set_developer_mode_status(self, enabled: bool) -> None:
        """Enable or disable Developer Mode via the AMFI XPC service."""
        cfreply = self._client.xpc.send_message_using_cf_serialization(
            "com.apple.amfi.xpc", {"action": int(not (enabled))}, False
        )["cfreply"]
        raw_response = next(iter(cfreply.values()))
        if b"success" not in raw_response:
            raise RpcSetDeveloperModeError()

    @property
    def developer_mode_status(self) -> bool:
        """Return True if Developer Mode is enabled."""
        return self._client.symbols.amfi_developer_mode_status()
