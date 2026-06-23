import logging
from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import BadReturnValueError
from rpcclient.utils import cached_async_method


if TYPE_CHECKING:
    from rpcclient.clients.ios.client import IosClient


class Backlight(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Display brightness controls."""

    def __init__(self, client: "IosClient[DarwinSymbolT_co]") -> None:
        self._client = client

    @cached_async_method
    async def _get_brightness(self) -> DarwinSymbolT_co:
        BrightnessSystemClient = await self._client.symbols.objc_getClass("BrightnessSystemClient")
        if not BrightnessSystemClient:
            logging.error("failed to load BrightnessSystemClient class")
        return await BrightnessSystemClient.objc_call("new")

    async def get_brightness(self) -> float:
        """Return the display brightness in the range 0.0-1.0."""
        return (
            await (
                await (await self._get_brightness()).objc_call(
                    "copyPropertyForKey:", await self._client.cf("DisplayBrightness")
                )
            ).py(dict)
        )["Brightness"]

    async def set_brightness(self, value: float) -> None:
        """Set the display brightness in the range 0.0-1.0."""
        if not await (await self._get_brightness()).objc_call(
            "setProperty:forKey:", await self._client.cf(value), await self._client.cf("DisplayBrightness")
        ):
            raise BadReturnValueError("failed to set DisplayBrightness")
