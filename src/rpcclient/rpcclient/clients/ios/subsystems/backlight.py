import logging
from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import BadReturnValueError
from rpcclient.utils import cached_async_method


if TYPE_CHECKING:
    from rpcclient.clients.ios.client import BaseIosClient


class Backlight(ClientBound["BaseIosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Display brightness controls."""

    def __init__(self, client: "BaseIosClient[DarwinSymbolT_co]") -> None:
        self._client = client

    @cached_async_method
    async def _get_brightness(self) -> DarwinSymbolT_co:
        BrightnessSystemClient = await self._client.symbols.objc_getClass.z("BrightnessSystemClient")
        if not BrightnessSystemClient:
            logging.error("failed to load BrightnessSystemClient class")
        return await BrightnessSystemClient.objc_call.z("new")

    @zyncio.zproperty
    async def _brightness(self) -> float:
        """Return the display brightness in the range 0.0-1.0."""
        return (
            await (
                await (await self._get_brightness()).objc_call.z(
                    "copyPropertyForKey:", await self._client.cf.z("DisplayBrightness")
                )
            ).py.z(dict)
        )["Brightness"]

    @_brightness.setter
    async def brightness(self, value: float) -> None:
        """Set the display brightness in the range 0.0-1.0."""
        if not await (await self._get_brightness()).objc_call.z(
            "setProperty:forKey:", await self._client.cf.z(value), await self._client.cf.z("DisplayBrightness")
        ):
            raise BadReturnValueError("failed to set DisplayBrightness")
