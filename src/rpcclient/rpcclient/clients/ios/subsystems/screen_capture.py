from collections import namedtuple
from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound


if TYPE_CHECKING:
    from rpcclient.clients.ios.client import BaseIosClient

CGRect = namedtuple("CGRect", "x0 y0 x1 y1")


class ScreenCapture(ClientBound["BaseIosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Screen capture utilities."""

    def __init__(self, client: "BaseIosClient[DarwinSymbolT_co]") -> None:
        self._client = client

    @zyncio.zproperty
    async def main_display(self) -> DarwinSymbolT_co:
        """Return the main CADisplay instance."""
        return await (await self._client.symbols.objc_getClass.z("CADisplay")).objc_call.z("mainDisplay")

    @zyncio.zproperty
    async def bounds(self) -> CGRect:
        """Return the main display bounds."""
        result = await (await type(self).main_display(self)).objc_call_raw.z("bounds")
        return CGRect(x0=result.d0, y0=result.d1, x1=result.d2, y1=result.d3)

    @zyncio.zproperty
    async def screenshot(self) -> bytes:
        """Return a PNG screenshot of the current screen."""
        return await (
            await self._client.symbols.UIImagePNGRepresentation.z(await self._client.symbols._UICreateScreenUIImage.z())
        ).py.z(bytes)
