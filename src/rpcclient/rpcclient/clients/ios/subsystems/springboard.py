from collections import namedtuple
from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import RpcFailedLaunchingAppError


if TYPE_CHECKING:
    from rpcclient.clients.ios.client import BaseIosClient

ScreenLockStatus = namedtuple("ScreenLockStatus", ["lock", "passcode"])


class SpringBoard(ClientBound["BaseIosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """SpringBoardServices helpers."""

    def __init__(self, client: "BaseIosClient[DarwinSymbolT_co]") -> None:
        self._client = client

    @zyncio.zmethod
    async def get_spring_board_server_port(self) -> int:
        """Return the SpringBoard server port."""
        return await self._client.symbols.SBSSpringBoardServerPort.z()

    @zyncio.zmethod
    async def launch_application(self, bundle_identifier: str) -> None:
        """Launch an app via SpringBoardServices."""
        err = await self._client.symbols.SBSLaunchApplicationWithIdentifier.z(
            await self._client.cf.z(bundle_identifier), 0
        )
        if err != 0:
            raise RpcFailedLaunchingAppError(
                f"SBSLaunchApplicationWithIdentifier failed with: error code {err} - "
                f"{await (await self._client.symbols.SBSApplicationLaunchingErrorString.z(err)).py.z()}"
            )

    @zyncio.zmethod
    async def get_screen_lock_status(self) -> ScreenLockStatus:
        """Return lockscreen and passcode status via SpringBoardServices."""
        server_port = await self.get_spring_board_server_port.z()
        async with self._client.safe_malloc.z(8) as p_is_lock, self._client.safe_malloc.z(8) as p_is_passcode:
            await p_is_lock.setindex(0, 0)
            await p_is_passcode.setindex(0, 0)
            await self._client.symbols.SBGetScreenLockStatus.z(server_port, p_is_lock, p_is_passcode)
            return ScreenLockStatus(await p_is_lock.getindex(0) == 1, await p_is_passcode.getindex(0) == 1)

    @zyncio.zmethod
    async def open_sensitive_url_and_unlock(self, url: str, unlock: bool = True) -> None:
        """Open a URL with the system handler, optionally unlocking."""
        screen_lock_status = await self.get_screen_lock_status.z()
        if not unlock and screen_lock_status.lock:
            if screen_lock_status.passcode:
                raise RpcFailedLaunchingAppError(
                    "cannot open url while screen is locked with passcode. you must unlock device first"
                )
            raise RpcFailedLaunchingAppError("cannot open url while screen is locked, use unlock=True parameter")
        cf_url_ref = await (await self._client.symbols.objc_getClass.z("NSURL")).objc_call.z(
            "URLWithString:", await self._client.cf.z(url)
        )
        if not await self._client.symbols.SBSOpenSensitiveURLAndUnlock.z(cf_url_ref, unlock):
            raise RpcFailedLaunchingAppError("SBSOpenSensitiveURLAndUnlock failed")
