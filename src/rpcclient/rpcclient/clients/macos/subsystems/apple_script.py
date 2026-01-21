import logging
from typing import TYPE_CHECKING, Optional

from rpcclient.exceptions import RpcAppleScriptError

if TYPE_CHECKING:
    from rpcclient.clients.macos.client import MacosClient

logger = logging.getLogger(__name__)


class AppleScript:
    def __init__(self, client: "MacosClient"):
        """
        :param client: rpcclient.macos.MacosClient
        """
        self._client = client

    def execute(self, script: str) -> None:
        with self._client.safe_malloc(8) as error:
            error[0] = 0
            apple_script = (
                self._client.symbols.objc_getClass("NSAppleScript")
                .objc_call("alloc")
                .objc_call("initWithSource:", self._client.cf(script))
            )
            apple_script.objc_call("executeAndReturnError:", error)
            if error[0]:
                raise RpcAppleScriptError(error[0].objc_call("description").py())
            apple_script.objc_call("release")

    def say(self, message: str, voice: Optional[str] = None):
        script = f'say "{message}"'
        if voice is not None:
            script += f' using "{voice}"'
        self.execute(script)

    def beep(self, count: int) -> None:
        self.execute(f"beep {count}")
