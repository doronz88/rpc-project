import logging
from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import RpcSetDeveloperModeError
from rpcclient.utils import assert_cast


if TYPE_CHECKING:
    from rpcclient.clients.ios.client import BaseIosClient

logger = logging.getLogger(__name__)


class Amfi(ClientBound["BaseIosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """AMFI utilities (AppleMobileFileIntegrity)."""

    def __init__(self, client: "BaseIosClient[DarwinSymbolT_co]") -> None:
        self._client = client
        self._client.load_framework_lazy("AppleMobileFileIntegrity")

    @zyncio.zmethod
    async def set_developer_mode_status(self, enabled: bool) -> None:
        """Enable or disable Developer Mode via the AMFI XPC service."""
        cfreply = assert_cast(
            dict,
            await self._client.xpc.send_message_using_cf_serialization.z(
                "com.apple.amfi.xpc", {"action": int(not (enabled))}, False
            ),
        )["cfreply"]
        raw_response = next(iter(cfreply.values()))
        if b"success" not in raw_response:
            raise RpcSetDeveloperModeError()

    @zyncio.zproperty
    async def developer_mode_status(self) -> bool:
        """Return True if Developer Mode is enabled."""
        return bool(await self._client.symbols.amfi_developer_mode_status.z())
