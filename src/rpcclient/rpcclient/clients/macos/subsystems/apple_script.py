import logging
from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import RpcAppleScriptError


if TYPE_CHECKING:
    from rpcclient.clients.macos.client import BaseMacosClient

logger = logging.getLogger(__name__)


class AppleScript(ClientBound["BaseMacosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "BaseMacosClient[DarwinSymbolT_co]") -> None:
        """
        :param client: rpcclient.macos.MacosClient
        """
        self._client = client

    @zyncio.zmethod
    async def execute(self, script: str) -> None:
        async with self._client.safe_malloc.z(8) as error:
            await error.setindex(0, 0)
            apple_script = await (
                await (await self._client.symbols.objc_getClass.z("NSAppleScript")).objc_call.z("alloc")
            ).objc_call.z("initWithSource:", await self._client.cf.z(script))
            await apple_script.objc_call.z("executeAndReturnError:", error)
            if await error.getindex(0):
                raise RpcAppleScriptError((await (await error.getindex(0)).objc_call.z("description")).py.z())
            await apple_script.objc_call.z("release")

    @zyncio.zmethod
    async def say(self, message: str, voice: str | None = None) -> None:
        script = f'say "{message}"'
        if voice is not None:
            script += f' using "{voice}"'
        await self.execute.z(script)

    @zyncio.zmethod
    async def beep(self, count: int) -> None:
        await self.execute.z(f"beep {count}")
