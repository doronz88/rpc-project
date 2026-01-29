from collections import namedtuple
from typing import TYPE_CHECKING

from rpcclient.clients.darwin.symbol import DarwinSymbol

if TYPE_CHECKING:
    from rpcclient.clients.ios.client import IosClient

CGRect = namedtuple("CGRect", "x0 y0 x1 y1")


class ScreenCapture:
    """Screen capture utilities."""

    def __init__(self, client: "IosClient") -> None:
        self._client = client

    @property
    def main_display(self) -> DarwinSymbol:
        """Return the main CADisplay instance."""
        return self._client.symbols.objc_getClass("CADisplay").objc_call("mainDisplay")

    @property
    def bounds(self) -> CGRect:
        """Return the main display bounds."""
        result = self.main_display.objc_call("bounds", return_raw=True)
        return CGRect(x0=result.d0, y0=result.d1, x1=result.d2, y1=result.d3)

    @property
    def screenshot(self) -> bytes:
        """Return a PNG screenshot of the current screen."""
        return self._client.symbols.UIImagePNGRepresentation(self._client.symbols._UICreateScreenUIImage()).py()
