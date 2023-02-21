import time
from typing import Union

from rpcclient.darwin.consts import kCGHIDEventTap, kCGNullWindowID, kCGWindowListOptionAll
from rpcclient.exceptions import BadReturnValueError


class CoreGraphics:
    """ Manage Core Graphics events. """

    def __init__(self, client):
        self._client = client

    @property
    def window_list(self):
        """
        get a list of all opened windows
        https://developer.apple.com/documentation/coregraphics/1455137-cgwindowlistcopywindowinfo?language=objc
        """
        return self._client.symbols.CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID).py()

    def send_key_press(self, key_code: int, interval: Union[float, int] = 0):
        """
        Send a key-press event.
        Accessibility features must be allowed.
        """
        self.send_keyboard_event(key_code, True)
        if interval:
            time.sleep(interval)
        self.send_keyboard_event(key_code, False)

    def send_keyboard_event(self, key_code: int, down: bool):
        """
        send a CG keyboard event
        https://developer.apple.com/documentation/coregraphics/1456564-cgeventcreatekeyboardevent
        """
        event = self._client.symbols.CGEventCreateKeyboardEvent(0, key_code, down)
        if not event:
            raise BadReturnValueError('CGEventCreateKeyboardEvent() failed')

        self._client.symbols.CGEventPost(kCGHIDEventTap, event)
