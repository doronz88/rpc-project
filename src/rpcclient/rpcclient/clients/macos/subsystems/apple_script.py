import logging
from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import RpcAppleScriptError


if TYPE_CHECKING:
    from rpcclient.clients.macos.client import MacosClient

logger = logging.getLogger(__name__)


class AppleScript(ClientBound["MacosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "MacosClient[DarwinSymbolT_co]") -> None:
        """
        :param client: rpcclient.macos.MacosClient
        """
        self._client = client

    async def execute(self, script: str) -> None:
        async with self._client.safe_malloc(8) as error:
            await error.setindex(0, 0)
            apple_script = await (
                await (await self._client.symbols.objc_getClass("NSAppleScript")).objc_call("alloc")
            ).objc_call("initWithSource:", await self._client.cf(script))
            await apple_script.objc_call("executeAndReturnError:", error)
            if await error.getindex(0):
                raise RpcAppleScriptError((await (await error.getindex(0)).objc_call("description")).py())
            await apple_script.objc_call("release")

    async def say(self, message: str, voice: str | None = None) -> None:
        script = f'say "{message}"'
        if voice is not None:
            script += f' using "{voice}"'
        await self.execute(script)

    async def beep(self, count: int) -> None:
        await self.execute(f"beep {count}")
