import logging
from typing import TYPE_CHECKING, Any, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.utils import cached_async_method


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from rpcclient.clients.ios.client import IosClient


class Call(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Represents a single ongoing call."""

    def __init__(
        self, client: "IosClient[DarwinSymbolT_co]", controller: DarwinSymbolT_co, call: DarwinSymbolT_co
    ) -> None:
        self._client = client
        self._controller: DarwinSymbolT_co = controller
        self._call: DarwinSymbolT_co = call

    async def disconnect(self) -> None:
        """Disconnect the current call."""
        await self._send_action("CXEndCallAction")

    async def answer(self) -> None:
        """Answer the current call."""
        await self._send_action("CXAnswerCallAction")

    async def _send_action(self, action_name: str) -> None:
        action_class = await self._client.symbols.objc_getClass(action_name)
        action = await (await action_class.objc_call("alloc")).objc_call("initWithCallUUID:", await self._uuid())
        await self._controller.objc_call(
            "requestTransactionWithAction:completion:", action, await self._client.get_dummy_block()
        )

    async def _uuid(self) -> Any:
        return await self._call.objc_call("UUID")


class Telephony(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Telephony utilities backed by CallKit and CoreTelephony.

    Accessing real telephony requires the entitlement "application-identifier"
    to be set to "com.apple.coretelephony".
    """

    def __init__(self, client: "IosClient[DarwinSymbolT_co]") -> None:
        self._client = client
        self._client.load_framework_lazy("CallKit")

    @cached_async_method
    async def cx_call_controller(self) -> DarwinSymbolT_co:
        return await (await self._client.symbols.objc_getClass("CXCallController")).objc_call("new")

    @cached_async_method
    async def cx_call_observer(self) -> DarwinSymbolT_co:
        return await (await type(self).cx_call_controller(self)).objc_call("callObserver")

    @cached_async_method
    async def ct_message_center(self) -> DarwinSymbolT_co:
        return await (await self._client.symbols.objc_getClass("CTMessageCenter")).objc_call("sharedMessageCenter")

    async def dial(self, number: str) -> None:
        """
        Start a call to a number.

        Use `current_call` to access the created call.
        """
        await self._client.symbols.CTCallDial(await self._client.cf(number))

    async def send_sms(self, to_address: str, text: str, smsc: str = "1111") -> None:
        """
        Send an SMS message.

        :param to_address: Destination phone address.
        :param text: Message text.
        :param smsc: Originator short message service center address.
        """
        await (await type(self).ct_message_center(self)).objc_call(
            "sendSMSWithText:serviceCenter:toAddress:",
            await self._client.cf(text),
            await self._client.cf(smsc),
            await self._client.cf(to_address),
        )

    async def current_call(self) -> Call | None:
        """
        Return an object representing the current active call, if any.
        """
        calls = await (await type(self).cx_call_observer(self)).objc_call("calls")
        call_count = await calls.objc_call("count")

        call_list = [await calls.objc_call("objectAtIndex:", i) for i in range(call_count)]

        for call_id in range(call_count):
            call = call_list[call_id]
            if await call.objc_call("hasEnded"):
                continue
            return Call(self._client, await type(self).cx_call_controller(self), call)

        return None
