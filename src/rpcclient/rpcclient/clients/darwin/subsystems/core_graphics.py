from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.consts import kCGHIDEventTap, kCGNullWindowID, kCGWindowListOptionAll
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import BadReturnValueError
from rpcclient.utils import zync_sleep


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient


class CoreGraphics(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Manage Core Graphics events."""

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client

    @zyncio.zproperty
    async def window_list(self):
        """
        get a list of all opened windows
        https://developer.apple.com/documentation/coregraphics/1455137-cgwindowlistcopywindowinfo?language=objc
        """
        return await (
            await self._client.symbols.CGWindowListCopyWindowInfo.z(kCGWindowListOptionAll, kCGNullWindowID)
        ).py.z()

    @zyncio.zmethod
    async def send_key_press(self, key_code: int, interval: float | int = 0) -> None:
        """
        Send a key-press event.
        Accessibility features must be allowed.
        """
        await self.send_keyboard_event.z(key_code, True)
        if interval:
            await zync_sleep(self._client.__zync_mode__, interval)
        await self.send_keyboard_event.z(key_code, False)

    @zyncio.zmethod
    async def send_keyboard_event(self, key_code: int, down: bool) -> None:
        """
        send a CG keyboard event
        https://developer.apple.com/documentation/coregraphics/1456564-cgeventcreatekeyboardevent
        """
        event = await self._client.symbols.CGEventCreateKeyboardEvent.z(0, key_code, down)
        if not event:
            raise BadReturnValueError("CGEventCreateKeyboardEvent() failed")

        await self._client.symbols.CGEventPost.z(kCGHIDEventTap, event)
