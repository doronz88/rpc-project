import logging

from rpcclient.exceptions import BadReturnValueError

logger = logging.getLogger(__name__)


class Power:
    """ Power utils """

    def __init__(self, client):
        self._client = client

    def reboot(self) -> None:
        if self._client.symbols.reboot().c_int64 == -1:
            raise BadReturnValueError()
