import asyncio
from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.consts import kCGHIDEventTap, kCGNullWindowID, kCGWindowListOptionAll
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import BadReturnValueError


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient


class CoreGraphics(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Manage Core Graphics events."""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client

    async def window_list(self):
        """
        get a list of all opened windows
        https://developer.apple.com/documentation/coregraphics/1455137-cgwindowlistcopywindowinfo?language=objc
        """
        return await (
            await self._client.symbols.CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID)
        ).py()

    async def send_key_press(self, key_code: int, interval: float | int = 0) -> None:
        """
        Send a key-press event.
        Accessibility features must be allowed.
        """
        await self.send_keyboard_event(key_code, True)
        if interval:
            await asyncio.sleep(interval)
        await self.send_keyboard_event(key_code, False)

    async def send_keyboard_event(self, key_code: int, down: bool) -> None:
        """
        send a CG keyboard event
        https://developer.apple.com/documentation/coregraphics/1456564-cgeventcreatekeyboardevent
        """
        event = await self._client.symbols.CGEventCreateKeyboardEvent(0, key_code, down)
        if not event:
            raise BadReturnValueError("CGEventCreateKeyboardEvent() failed")

        await self._client.symbols.CGEventPost(kCGHIDEventTap, event)
