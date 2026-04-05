from collections.abc import AsyncGenerator
from enum import Enum
from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.consts import (
    IOHIDDigitizerEventMask,
    IOHIDDigitizerTransducerType,
    IOHIDEventField,
    IOHIDEventFieldDigitizer,
    kCFAllocatorDefault,
    kHIDPage_Consumer,
    kHIDUsage_Csmr_ACSearch,
    kHIDUsage_Csmr_FastForward,
    kHIDUsage_Csmr_Menu,
    kHIDUsage_Csmr_Mute,
    kHIDUsage_Csmr_Pause,
    kHIDUsage_Csmr_Play,
    kHIDUsage_Csmr_PlayOrPause,
    kHIDUsage_Csmr_Power,
    kHIDUsage_Csmr_RandomPlay,
    kHIDUsage_Csmr_Repeat,
    kHIDUsage_Csmr_Rewind,
    kHIDUsage_Csmr_VolumeDecrement,
    kHIDUsage_Csmr_VolumeIncrement,
)
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import BadReturnValueError
from rpcclient.utils import zync_sleep


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient


class TouchEventType(Enum):
    TOUCH_DOWN = 0
    TOUCH_UP = 1
    TOUCH_MOVE = 2


TOUCH_EVENT_SLEEP = 0.1


EVENT_TYPE_PARAMS = {
    TouchEventType.TOUCH_DOWN: {
        "event_flags": (
            IOHIDDigitizerEventMask.kIOHIDDigitizerEventAttribute.value
            | IOHIDDigitizerEventMask.kIOHIDDigitizerEventTouch.value
            | IOHIDDigitizerEventMask.kIOHIDDigitizerEventIdentity.value
        ),
        "button_mask": 1,
        "touch": True,
    },
    TouchEventType.TOUCH_MOVE: {
        "event_flags": (
            IOHIDDigitizerEventMask.kIOHIDDigitizerEventPosition.value
            | IOHIDDigitizerEventMask.kIOHIDDigitizerEventAttribute.value
        ),
        "button_mask": 1,
        "touch": True,
    },
    TouchEventType.TOUCH_UP: {
        "event_flags": (
            IOHIDDigitizerEventMask.kIOHIDDigitizerEventAttribute.value
            | IOHIDDigitizerEventMask.kIOHIDDigitizerEventTouch.value
            | IOHIDDigitizerEventMask.kIOHIDDigitizerEventIdentity.value
        ),
        "button_mask": 0,
        "touch": False,
    },
}


class Hid(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Control HID devices and simulate events"""

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client

    @zyncio.zmethod
    async def send_double_home_button_press(self) -> None:
        await self.send_home_button_press.z()
        await self.send_home_button_press.z()

    @zyncio.zmethod
    async def send_rewind_button_press(self) -> None:
        await self.send_key_press.z(kHIDPage_Consumer, kHIDUsage_Csmr_Rewind)

    @zyncio.zmethod
    async def send_random_play_button_press(self) -> None:
        await self.send_key_press.z(kHIDPage_Consumer, kHIDUsage_Csmr_RandomPlay)

    @zyncio.zmethod
    async def send_repeat_button_press(self) -> None:
        await self.send_key_press.z(kHIDPage_Consumer, kHIDUsage_Csmr_Repeat)

    @zyncio.zmethod
    async def send_fast_forward_button_press(self) -> None:
        await self.send_key_press.z(kHIDPage_Consumer, kHIDUsage_Csmr_FastForward)

    @zyncio.zmethod
    async def send_play_button_press(self) -> None:
        await self.send_key_press.z(kHIDPage_Consumer, kHIDUsage_Csmr_Play)

    @zyncio.zmethod
    async def send_pause_button_press(self) -> None:
        await self.send_key_press.z(kHIDPage_Consumer, kHIDUsage_Csmr_Pause)

    @zyncio.zmethod
    async def send_play_pause_button_press(self) -> None:
        await self.send_key_press.z(kHIDPage_Consumer, kHIDUsage_Csmr_PlayOrPause)

    @zyncio.zmethod
    async def send_search_button_press(self) -> None:
        await self.send_key_press.z(kHIDPage_Consumer, kHIDUsage_Csmr_ACSearch)

    @zyncio.zmethod
    async def send_mute_button_press(self) -> None:
        await self.send_key_press.z(kHIDPage_Consumer, kHIDUsage_Csmr_Mute)

    @zyncio.zmethod
    async def send_home_button_press(self) -> None:
        await self.send_key_press.z(kHIDPage_Consumer, kHIDUsage_Csmr_Menu)

    @zyncio.zmethod
    async def send_power_button_press(self, interval: int = 0) -> None:
        await self.send_key_press.z(kHIDPage_Consumer, kHIDUsage_Csmr_Power, interval=interval)

    @zyncio.zmethod
    async def send_volume_down_button_press(self, interval: int = 0) -> None:
        await self.send_key_press.z(kHIDPage_Consumer, kHIDUsage_Csmr_VolumeDecrement, interval=interval)

    @zyncio.zmethod
    async def send_volume_up_button_press(self, interval: int = 0) -> None:
        await self.send_key_press.z(kHIDPage_Consumer, kHIDUsage_Csmr_VolumeIncrement, interval=interval)

    @zyncio.zmethod
    async def send_key_press(self, page: int, key_code: int, interval: float | int = 0) -> None:
        await self.send_keyboard_event.z(page, key_code, True)
        if interval:
            await zync_sleep(self._client.__zync_mode__, interval)
        await self.send_keyboard_event.z(page, key_code, False)

    @zyncio.zmethod
    async def send_keyboard_event(self, page: int, key_code: int, down: bool) -> None:
        event = await self._client.symbols.IOHIDEventCreateKeyboardEvent.z(
            kCFAllocatorDefault, await self._client.symbols.mach_absolute_time.z(), page, key_code, down, 0
        )
        if not event:
            raise BadReturnValueError("IOHIDEventCreateKeyboardEvent() failed")

        await self.dispatch.z(event)

    @zyncio.zmethod
    async def send_swipe_right(self) -> None:
        await self.send_swipe.z(0.5, 0.5, 1.0, 0.5)

    @zyncio.zmethod
    async def send_swipe_left(self) -> None:
        await self.send_swipe.z(0.5, 0.5, 0.0, 0.5)

    @zyncio.zmethod
    async def send_swipe_up(self) -> None:
        await self.send_swipe.z(0.5, 1.5, 0.5, 0.5)

    @zyncio.zmethod
    async def send_swipe_down(self) -> None:
        await self.send_swipe.z(0.5, 0.5, 0.5, 1.5)

    @zyncio.zmethod
    async def send_swipe(self, from_x: float, from_y: float, to_x: float, to_y: float) -> None:
        await self.send_touch_event.z(TouchEventType.TOUCH_DOWN, from_x, from_y)
        await zync_sleep(self._client.__zync_mode__, TOUCH_EVENT_SLEEP)
        await self.send_touch_event.z(TouchEventType.TOUCH_MOVE, to_x, to_y)
        await self.send_touch_event.z(TouchEventType.TOUCH_UP, to_x, to_y)

    @zyncio.zmethod
    async def send_touch_event(self, event_type: TouchEventType, x: float, y: float, pressure: float = 0.4) -> None:
        params = EVENT_TYPE_PARAMS[event_type]

        timestamp = await self._client.symbols.mach_absolute_time.z()

        event_flags = params["event_flags"]
        touch = params["touch"]
        button_mask = params["button_mask"]

        parent = await self.create_digitizer_event.z(
            IOHIDDigitizerTransducerType.kIOHIDDigitizerTransducerTypeHand,
            0,
            0,
            event_flags,
            0,
            x,
            y,
            0.0,
            0.0,
            0.0,
            touch,
            touch,
            0,
            timestamp=timestamp,
        )

        child = await self.create_digitizer_finger_event.z(
            2, 2, event_flags, button_mask, x, y, 0.0, pressure, 0.0, touch, touch, 0, timestamp=timestamp
        )
        await self._client.symbols.IOHIDEventAppendEvent.z(parent, child)
        await self.dispatch.z(parent)

    @zyncio.zmethod
    async def create_digitizer_event(
        self,
        type_: IOHIDDigitizerTransducerType | int,
        index: int,
        identity: int,
        event_mask: int,
        button_mask: int,
        x: float,
        y: float,
        z: float,
        tip_pressure: float,
        barrel_pressure: float,
        range_: bool,
        touch: bool,
        options: int,
        timestamp=None,
    ):
        if timestamp is None:
            timestamp = await self._client.symbols.mach_absolute_time.z()

        event = await self._client.symbols.IOHIDEventCreateDigitizerEvent.z(
            kCFAllocatorDefault,
            timestamp,
            type_,
            index,
            identity,
            event_mask,
            button_mask,
            x,
            y,
            z,
            tip_pressure,
            barrel_pressure,
            range_,
            touch,
            options,
        )

        if not event:
            raise BadReturnValueError("IOHIDEventCreateDigitizerEvent() failed")

        await self._client.symbols.IOHIDEventSetIntegerValue.z(event, IOHIDEventField.kIOHIDEventFieldIsBuiltIn, 0)
        await self._client.symbols.IOHIDEventSetIntegerValue.z(
            event, IOHIDEventFieldDigitizer.kIOHIDEventFieldDigitizerIsDisplayIntegrated, 1
        )
        await self._client.symbols.IOHIDEventSetSenderID.z(event, 0x8000000817319375)

        return event

    @zyncio.zmethod
    async def create_digitizer_finger_event(
        self,
        index: int,
        identity: int,
        event_mask: int,
        button_mask: int,
        x: float,
        y: float,
        z: float,
        tip_pressure: float,
        twist: float,
        range_: bool,
        touch: bool,
        options: int,
        timestamp=None,
    ) -> DarwinSymbolT_co:
        if timestamp is None:
            timestamp = await self._client.symbols.mach_absolute_time.z()

        event = await self._client.symbols.IOHIDEventCreateDigitizerFingerEvent.z(
            kCFAllocatorDefault,
            timestamp,
            index,
            identity,
            event_mask,
            button_mask,
            x,
            y,
            z,
            tip_pressure,
            twist,
            range_,
            touch,
            options,
        )

        if not event:
            raise BadReturnValueError("IOHIDEventCreateDigitizerFingerEvent() failed")

        await self._client.symbols.IOHIDEventSetFloatValue.z(
            event, IOHIDEventFieldDigitizer.kIOHIDEventFieldDigitizerMajorRadius, 0.5
        )
        return event

    @zyncio.zcontextmanagermethod
    async def create_hid_client(self) -> AsyncGenerator[DarwinSymbolT_co]:
        client = await self._client.symbols.IOHIDEventSystemClientCreate.z(0)

        if not client:
            raise BadReturnValueError("IOHIDEventSystemClientCreate() failed")

        try:
            yield client
        finally:
            await self._client.symbols.CFRelease.z(client)

    @zyncio.zmethod
    async def dispatch(self, event):
        async with self.create_hid_client.z() as hid_client:
            await self._client.symbols.IOHIDEventSystemClientDispatchEvent.z(hid_client, event)
