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
        self.cx_call_controller = self._client.symbols.objc_getClass('CXCallController').objc_call('new')
        self.cx_call_observer = self.cx_call_controller.objc_call('callObserver')

    def dial(self, number: str):
        """
        Start a call to a number. Use `current_call` to access the created call.
        :param number: Phone address to call to.
        """
        self._client.symbols.CTCallDial(self._client.cf(number))

    @property
    def current_call(self) -> Call:
        """
        Return on object representing the current active call.
        """
        calls = self.cx_call_observer.objc_call('calls')
        for call_id in range(calls.objc_call('count')):
            call = calls.py()[call_id]
            if call.objc_call('hasEnded'):
                continue
            return Call(self._client, self.cx_call_controller, call)
