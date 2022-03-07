import contextlib
import time

from rpcclient.darwin.consts import kCFAllocatorDefault, kHIDUsage_Csmr_Menu, kHIDUsage_Csmr_Power, \
    kHIDUsage_Csmr_VolumeDecrement, kHIDUsage_Csmr_VolumeIncrement, kHIDPage_Consumer, kHIDUsage_Csmr_Mute, \
    kHIDUsage_Csmr_ACSearch, kHIDUsage_Csmr_PlayOrPause, kHIDUsage_Csmr_Play, kHIDUsage_Csmr_Pause, \
    kHIDUsage_Csmr_Rewind, kHIDUsage_Csmr_RandomPlay, kHIDUsage_Csmr_Repeat, kHIDUsage_Csmr_FastForward
from rpcclient.exceptions import BadReturnValueError


class Hid:
    """ Control HID devices and simulate events """

    def __init__(self, client):
        self._client = client

    def send_double_home_button_press(self):
        self.send_home_button_press()
        self.send_home_button_press()

    def send_rewind_button_press(self):
        self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Rewind)

    def send_random_play_button_press(self):
        self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_RandomPlay)

    def send_repeat_button_press(self):
        self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Repeat)

    def send_fast_forward_button_press(self):
        self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_FastForward)

    def send_play_button_press(self):
        self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Play)

    def send_pause_button_press(self):
        self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Pause)

    def send_play_pause_button_press(self):
        self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_PlayOrPause)

    def send_search_button_press(self):
        self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_ACSearch)

    def send_mute_button_press(self):
        self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Mute)

    def send_home_button_press(self):
        self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Menu)

    def send_power_button_press(self, interval: int = 0):
        self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Power, interval=interval)

    def send_volume_down_button_press(self, interval: int = 0):
        self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_VolumeDecrement, interval=interval)

    def send_volume_up_button_press(self, interval: int = 0):
        self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_VolumeIncrement, interval=interval)

    def send_key_press(self, page: int, key_code: int, interval: int = 0):
        self.send_keyboard_event(page, key_code, True)
        if interval:
            time.sleep(interval)
        self.send_keyboard_event(page, key_code, False)

    def send_keyboard_event(self, page: int, key_code: int, down: bool):
        event = self._client.symbols.IOHIDEventCreateKeyboardEvent(kCFAllocatorDefault,
                                                                   self._client.symbols.mach_absolute_time(),
                                                                   page, key_code, down, 0)
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
