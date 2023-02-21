import contextlib
import time
from enum import Enum
from typing import Union

from rpcclient.darwin.consts import IOHIDDigitizerEventMask, IOHIDDigitizerTransducerType, IOHIDEventField, \
    IOHIDEventFieldDigitizer, kCFAllocatorDefault, kHIDPage_Consumer, kHIDUsage_Csmr_ACSearch, \
    kHIDUsage_Csmr_FastForward, kHIDUsage_Csmr_Menu, kHIDUsage_Csmr_Mute, kHIDUsage_Csmr_Pause, kHIDUsage_Csmr_Play, \
    kHIDUsage_Csmr_PlayOrPause, kHIDUsage_Csmr_Power, kHIDUsage_Csmr_RandomPlay, kHIDUsage_Csmr_Repeat, \
    kHIDUsage_Csmr_Rewind, kHIDUsage_Csmr_VolumeDecrement, kHIDUsage_Csmr_VolumeIncrement
from rpcclient.exceptions import BadReturnValueError


class TouchEventType(Enum):
    TOUCH_DOWN = 0
    TOUCH_UP = 1
    TOUCH_MOVE = 2


TOUCH_EVENT_SLEEP = 0.1


EVENT_TYPE_PARAMS = {
    TouchEventType.TOUCH_DOWN: {
        'event_flags': (IOHIDDigitizerEventMask.kIOHIDDigitizerEventAttribute.value |
                        IOHIDDigitizerEventMask.kIOHIDDigitizerEventTouch.value |
                        IOHIDDigitizerEventMask.kIOHIDDigitizerEventIdentity.value),
        'button_mask': 1,
        'touch': True,
    },
    TouchEventType.TOUCH_MOVE: {
        'event_flags': (IOHIDDigitizerEventMask.kIOHIDDigitizerEventPosition.value |
                        IOHIDDigitizerEventMask.kIOHIDDigitizerEventAttribute.value),
        'button_mask': 1,
        'touch': True,
    },
    TouchEventType.TOUCH_UP: {
        'event_flags': (IOHIDDigitizerEventMask.kIOHIDDigitizerEventAttribute.value |
                        IOHIDDigitizerEventMask.kIOHIDDigitizerEventTouch.value |
                        IOHIDDigitizerEventMask.kIOHIDDigitizerEventIdentity.value),
        'button_mask': 0,
        'touch': False,
    },
}


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

    def send_key_press(self, page: int, key_code: int, interval: Union[float, int] = 0):
        self.send_keyboard_event(page, key_code, True)
        if interval:
            time.sleep(interval)
        self.send_keyboard_event(page, key_code, False)

    def send_keyboard_event(self, page: int, key_code: int, down: bool):
        event = self._client.symbols.IOHIDEventCreateKeyboardEvent(kCFAllocatorDefault,
                                                                   self._client.symbols.mach_absolute_time(),
                                                                   page, key_code, down, 0)
        if not event:
            raise BadReturnValueError('IOHIDEventCreateKeyboardEvent() failed')

        self.dispatch(event)

    def send_swipe_right(self):
        self.send_swipe(0.5, 0.5, 1.0, 0.5)

    def send_swipe_left(self):
        self.send_swipe(0.5, 0.5, 0.0, 0.5)

    def send_swipe_up(self):
        self.send_swipe(0.5, 1.5, 0.5, 0.5)

    def send_swipe_down(self):
        self.send_swipe(0.5, 0.5, 0.5, 1.5)

    def send_swipe(self, from_x: float, from_y: float, to_x: float, to_y: float):
        self.send_touch_event(TouchEventType.TOUCH_DOWN, from_x, from_y)
        time.sleep(TOUCH_EVENT_SLEEP)
        self.send_touch_event(TouchEventType.TOUCH_MOVE, to_x, to_y)
        self.send_touch_event(TouchEventType.TOUCH_UP, to_x, to_y)

    def send_touch_event(self, event_type: TouchEventType, x: float, y: float, pressure: float = 0.4):
        params = EVENT_TYPE_PARAMS[event_type]

        timestamp = self._client.symbols.mach_absolute_time()

        event_flags = params['event_flags']
        touch = params['touch']
        button_mask = params['button_mask']

        parent = self.create_digitizer_event(IOHIDDigitizerTransducerType.kIOHIDDigitizerTransducerTypeHand,
                                             0, 0, event_flags, 0, x, y, 0.0, 0.0, 0.0, touch, touch, 0,
                                             timestamp=timestamp)

        child = self.create_digitizer_finger_event(2, 2, event_flags, button_mask, x, y, 0.0, pressure, 0.0,
                                                   touch, touch, 0, timestamp=timestamp)
        self._client.symbols.IOHIDEventAppendEvent(parent, child)
        self.dispatch(parent)

    def create_digitizer_event(self, type_: Union[IOHIDDigitizerTransducerType, int], index: int, identity: int,
                               event_mask: int, button_mask: int, x: float, y: float, z: float, tip_pressure: float,
                               barrel_pressure: float, range_: bool, touch: bool, options: int, timestamp=None):
        if timestamp is None:
            timestamp = self._client.symbols.mach_absolute_time()

        event = self._client.symbols.IOHIDEventCreateDigitizerEvent(
            kCFAllocatorDefault, timestamp, type_, index, identity, event_mask,
            button_mask, x, y, z, tip_pressure, barrel_pressure, range_, touch, options)

        if not event:
            raise BadReturnValueError('IOHIDEventCreateDigitizerEvent() failed')

        self._client.symbols.IOHIDEventSetIntegerValue(event, IOHIDEventField.kIOHIDEventFieldIsBuiltIn, 0)
        self._client.symbols.IOHIDEventSetIntegerValue(
            event, IOHIDEventFieldDigitizer.kIOHIDEventFieldDigitizerIsDisplayIntegrated, 1)
        self._client.symbols.IOHIDEventSetSenderID(event, 0x8000000817319375)

        return event

    def create_digitizer_finger_event(self, index: int, identity: int, event_mask: int,
                                      button_mask: int, x: float, y: float, z: float, tip_pressure: float,
                                      twist: float, range_: bool, touch: bool, options: int, timestamp=None):
        if timestamp is None:
            timestamp = self._client.symbols.mach_absolute_time()

        event = self._client.symbols.IOHIDEventCreateDigitizerFingerEvent(
            kCFAllocatorDefault, timestamp, index, identity, event_mask,
            button_mask, x, y, z, tip_pressure, twist, range_, touch, options)

        if not event:
            raise BadReturnValueError('IOHIDEventCreateDigitizerFingerEvent() failed')

        self._client.symbols.IOHIDEventSetFloatValue(
            event, IOHIDEventFieldDigitizer.kIOHIDEventFieldDigitizerMajorRadius, 0.5)
        return event

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
