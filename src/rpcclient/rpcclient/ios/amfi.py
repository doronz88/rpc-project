import logging

from rpcclient.exceptions import RpcSetDeveloperModeError
from rpcclient.structs.consts import RTLD_NOW

logger = logging.getLogger(__name__)


class Amfi:
    """ AMFI utils """

    def __init__(self, client):
        self._client = client
        self._load_amfi()

    def set_developer_mode_status(self, enabled: bool) -> None:
        cfreply = self._client.xpc.send_message_using_cf_serialization(
            'com.apple.amfi.xpc', {'action': int(not (enabled))}, False)['cfreply']
        raw_response = list(cfreply.values())[0]
        if b'success' not in raw_response:
            raise RpcSetDeveloperModeError()

    @property
    def developer_mode_status(self) -> bool:
        """ get Developer Mode status """
        return self._client.symbols.amfi_developer_mode_status()

    def _load_amfi(self):
        options = [
            '/System/Library/PrivateFrameworks/AppleMobileFileIntegrity.framework/AppleMobileFileIntegrity',
        ]
        for option in options:
            if self._client.dlopen(option, RTLD_NOW):
                return
        logger.warning('AppleMobileFileIntegrity library isn\'t available')
