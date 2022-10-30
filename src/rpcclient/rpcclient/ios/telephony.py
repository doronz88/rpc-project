import logging

from rpcclient.structs.consts import RTLD_NOW

logger = logging.getLogger(__name__)


class Call:
    def __init__(self, client, controller, call):
        self._client = client
        self._controller = controller
        self._call = call

    def disconnect(self):
        """
        Disconnect the current call.
        """
        self._send_action('CXEndCallAction')

    def answer(self):
        """
        Answer the current call.
        """
        self._send_action('CXAnswerCallAction')

    def _send_action(self, action_name):
        action_class = self._client.symbols.objc_getClass(action_name)
        action = action_class.objc_call('alloc').objc_call('initWithCallUUID:', self._uuid)
        self._controller.objc_call('requestTransactionWithAction:completion:', action, self._client.get_dummy_block())

    @property
    def _uuid(self):
        return self._call.objc_call('UUID')


class Telephony:
    """
    Telephony utils.
    In order to access the real telephony, the API requires the entitlement "application-identifier" to be set to
    "com.apple.coretelephony".
    """

    def __init__(self, client):
        self._client = client
        self._load_callkit_library()
        self.cx_call_controller = self._client.symbols.objc_getClass('CXCallController').objc_call('new')
        self.cx_call_observer = self.cx_call_controller.objc_call('callObserver')
        self.ct_message_center = self._client.symbols.objc_getClass('CTMessageCenter').objc_call('sharedMessageCenter')

    def dial(self, number: str):
        """
        Start a call to a number. Use `current_call` to access the created call.
        :param number: Phone address to call to.
        """
        self._client.symbols.CTCallDial(self._client.cf(number))

    def send_sms(self, to_address: str, text: str, smsc: str = '1111'):
        """
        Send a SMS.
        :param to_address: Phone address to send to.
        :param text: Message text.
        :param smsc: Originator's short message service center address.
        """
        self.ct_message_center.objc_call(
            'sendSMSWithText:serviceCenter:toAddress:', self._client.cf(text), self._client.cf(smsc),
            self._client.cf(to_address)
        )

    @property
    def current_call(self) -> Call:
        """
        Return on object representing the current active call.
        """
        calls = self.cx_call_observer.objc_call('calls')
        call_count = calls.objc_call('count')

        call_list = []
        for i in range(call_count):
            call_list.append(calls.objc_call('objectAtIndex:', i))

        for call_id in range(call_count):
            call = call_list[call_id]
            if call.objc_call('hasEnded'):
                continue
            return Call(self._client, self.cx_call_controller, call)

    def _load_callkit_library(self):
        options = [
            '/System/Library/Frameworks/CallKit.framework/CallKit'
        ]
        for option in options:
            if self._client.dlopen(option, RTLD_NOW):
                return
        logger.warning('CallKit library isn\'t available')
