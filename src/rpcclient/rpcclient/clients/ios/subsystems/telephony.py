import logging
from typing import TYPE_CHECKING, Any, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.utils import cached_async_method


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from rpcclient.clients.ios.client import BaseIosClient


class Call(ClientBound["BaseIosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Represents a single ongoing call."""

    def __init__(
        self, client: "BaseIosClient[DarwinSymbolT_co]", controller: DarwinSymbolT_co, call: DarwinSymbolT_co
    ) -> None:
        self._client = client
        self._controller: DarwinSymbolT_co = controller
        self._call: DarwinSymbolT_co = call

    @zyncio.zmethod
    async def disconnect(self) -> None:
        """Disconnect the current call."""
        await self._send_action("CXEndCallAction")

    @zyncio.zmethod
    async def answer(self) -> None:
        """Answer the current call."""
        await self._send_action("CXAnswerCallAction")

    async def _send_action(self, action_name: str) -> None:
        action_class = await self._client.symbols.objc_getClass.z(action_name)
        action = await (await action_class.objc_call.z("alloc")).objc_call.z("initWithCallUUID:", await self._uuid())
        await self._controller.objc_call.z(
            "requestTransactionWithAction:completion:", action, await self._client.get_dummy_block.z()
        )

    async def _uuid(self) -> Any:
        return await self._call.objc_call.z("UUID")


class Telephony(ClientBound["BaseIosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Telephony utilities backed by CallKit and CoreTelephony.

    Accessing real telephony requires the entitlement "application-identifier"
    to be set to "com.apple.coretelephony".
    """

    def __init__(self, client: "BaseIosClient[DarwinSymbolT_co]") -> None:
        self._client = client
        self._client.load_framework_lazy("CallKit")

    @zyncio.zproperty
    @cached_async_method
    async def cx_call_controller(self) -> DarwinSymbolT_co:
        return await (await self._client.symbols.objc_getClass.z("CXCallController")).objc_call.z("new")

    @zyncio.zproperty
    @cached_async_method
    async def cx_call_observer(self) -> DarwinSymbolT_co:
        return await (await type(self).cx_call_controller(self)).objc_call.z("callObserver")

    @zyncio.zproperty
    @cached_async_method
    async def ct_message_center(self) -> DarwinSymbolT_co:
        return await (await self._client.symbols.objc_getClass.z("CTMessageCenter")).objc_call.z("sharedMessageCenter")

    @zyncio.zmethod
    async def dial(self, number: str) -> None:
        """
        Start a call to a number.

        Use `current_call` to access the created call.
        """
        await self._client.symbols.CTCallDial.z(await self._client.cf.z(number))

    @zyncio.zmethod
    async def send_sms(self, to_address: str, text: str, smsc: str = "1111") -> None:
        """
        Send an SMS message.

        :param to_address: Destination phone address.
        :param text: Message text.
        :param smsc: Originator short message service center address.
        """
        await (await type(self).ct_message_center(self)).objc_call.z(
            "sendSMSWithText:serviceCenter:toAddress:",
            await self._client.cf.z(text),
            await self._client.cf.z(smsc),
            await self._client.cf.z(to_address),
        )

    @zyncio.zproperty
    async def current_call(self) -> Call | None:
        """
        Return an object representing the current active call, if any.
        """
        calls = await (await type(self).cx_call_observer(self)).objc_call.z("calls")
        call_count = await calls.objc_call.z("count")

        call_list = [await calls.objc_call.z("objectAtIndex:", i) for i in range(call_count)]

        for call_id in range(call_count):
            call = call_list[call_id]
            if await call.objc_call.z("hasEnded"):
                continue
            return Call(self._client, await type(self).cx_call_controller(self), call)

        return None
