import contextlib
import logging
import time
from enum import Enum

from rpcclient.darwin.consts import kCFAllocatorDefault
from rpcclient.exceptions import BadReturnValueError

logger = logging.getLogger(__name__)


class Keycode(Enum):
    VOLUME_UP = 0xe9
    VOLUME_DOWN = 0xea
    HOME = 0x40
    POWER = 0x30


class Hid:
    def __init__(self, client):
        self._client = client

    def send_double_home_button_press(self):
        self.send_home_button_press()
        self.send_home_button_press()

    def send_home_button_press(self):
        self.send_key_press(Keycode.HOME.value)

    def send_power_button_press(self, interval: int = 0):
        self.send_key_press(Keycode.POWER.value, interval=interval)

    def send_volume_down_button_press(self, interval: int = 0):
        self.send_key_press(Keycode.VOLUME_DOWN.value, interval=interval)

    def send_volume_up_button_press(self, interval: int = 0):
        self.send_key_press(Keycode.VOLUME_UP.value, interval=interval)

    def send_key_press(self, key_code: int, interval: int = 0):
        self.send_keyboard_event(key_code, True)
        if interval:
            time.sleep(interval)
        self.send_keyboard_event(key_code, False)

    def send_keyboard_event(self, key_code: int, down: bool):
        event = self._client.symbols.IOHIDEventCreateKeyboardEvent(kCFAllocatorDefault,
                                                                   self._client.symbols.mach_absolute_time(),
                                                                   0x0c, key_code, down, 0)
        self.dispatch(event)

    @contextlib.contextmanager
    def create_hid_client(self):
        client = self._client.symbols.IOHIDEventSystemClientCreate(0)

        if not client:
            raise BadReturnValueError('IOHIDEventSystemClientCreate() failed')

        try:
            yield client
        finally:
            self._client.symbols.CFRelease(client)

    def dispatch(self, event):
        with self.create_hid_client() as hid_client:
            self._client.symbols.IOHIDEventSystemClientDispatchEvent(hid_client, event)
