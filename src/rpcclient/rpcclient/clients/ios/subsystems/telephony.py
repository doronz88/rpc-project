import logging
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from rpcclient.clients.ios.client import IosClient


class Call:
    """Represents a single ongoing call."""

    def __init__(self, client: "IosClient", controller: Any, call: Any) -> None:
        self._client = client
        self._controller = controller
        self._call = call

    def disconnect(self) -> None:
        """Disconnect the current call."""
        self._send_action("CXEndCallAction")

    def answer(self) -> None:
        """Answer the current call."""
        self._send_action("CXAnswerCallAction")

    def _send_action(self, action_name: str) -> None:
        action_class = self._client.symbols.objc_getClass(action_name)
        action = action_class.objc_call("alloc").objc_call("initWithCallUUID:", self._uuid)
        self._controller.objc_call("requestTransactionWithAction:completion:", action, self._client.get_dummy_block())

    @property
    def _uuid(self) -> UUID:
        return self._call.objc_call("UUID")


class Telephony:
    """
    Telephony utilities backed by CallKit and CoreTelephony.

    Accessing real telephony requires the entitlement "application-identifier"
    to be set to "com.apple.coretelephony".
    """

    def __init__(self, client: "IosClient") -> None:
        self._client = client
        self._client.load_framework("CallKit")
        self.cx_call_controller = self._client.symbols.objc_getClass("CXCallController").objc_call("new")
        self.cx_call_observer = self.cx_call_controller.objc_call("callObserver")
        self.ct_message_center = self._client.symbols.objc_getClass("CTMessageCenter").objc_call("sharedMessageCenter")

    def dial(self, number: str) -> None:
        """
        Start a call to a number.

        Use `current_call` to access the created call.
        """
        self._client.symbols.CTCallDial(self._client.cf(number))

    def send_sms(self, to_address: str, text: str, smsc: str = "1111") -> None:
        """
        Send an SMS message.

        :param to_address: Destination phone address.
        :param text: Message text.
        :param smsc: Originator short message service center address.
        """
        self.ct_message_center.objc_call(
            "sendSMSWithText:serviceCenter:toAddress:",
            self._client.cf(text),
            self._client.cf(smsc),
            self._client.cf(to_address),
        )

    @property
    def current_call(self) -> Optional[Call]:
        """
        Return an object representing the current active call, if any.
        """
        calls = self.cx_call_observer.objc_call("calls")
        call_count = calls.objc_call("count")

        call_list = []
        for i in range(call_count):
            call_list.append(calls.objc_call("objectAtIndex:", i))

        for call_id in range(call_count):
            call = call_list[call_id]
            if call.objc_call("hasEnded"):
                continue
            return Call(self._client, self.cx_call_controller, call)

        return None
