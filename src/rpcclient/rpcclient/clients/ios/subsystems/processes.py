import logging
from datetime import datetime, timedelta

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.subsystems.processes import DarwinProcesses, Process
from rpcclient.core.structs.consts import SIGKILL
from rpcclient.exceptions import LaunchError


logger = logging.getLogger(__name__)


class IosProcesses(DarwinProcesses[DarwinSymbolT_co]):
    @zyncio.zmethod
    async def launch(
        self,
        bundle_id: str,
        kill_existing: bool = True,
        timeout: float = 1,
        unlock_device: bool = True,
        disable_aslr: bool = False,
        wait_for_debugger: bool = False,
        stdout: str | None = None,
        stderr: str | None = None,
    ) -> Process:
        """
        Launch an app via BackBoardServices with optional debug options.

        BackBoardServices reference:
        https://github.com/swigger/debugserver-ios/blob/master/inc/BackBoardServices.framework/Headers/BackBoardServices.h
        """
        debug_options = {}
        options = {}
        sym = self._client.symbols
        debug_options[await (await sym.BKSDebugOptionKeyDisableASLR.getindex(0)).py.z()] = disable_aslr
        debug_options[await (await sym.BKSDebugOptionKeyWaitForDebugger.getindex(0)).py.z()] = wait_for_debugger
        if stdout is not None:
            debug_options[await (await sym.BKSDebugOptionKeyStandardOutPath.getindex(0)).py.z()] = stdout
        if stderr is not None:
            debug_options[await (await sym.BKSDebugOptionKeyStandardErrorPath.getindex(0)).py.z()] = stderr
        options[await (await sym.BKSOpenApplicationOptionKeyUnlockDevice.getindex(0)).py.z()] = unlock_device
        options[await (await sym.BKSOpenApplicationOptionKeyDebuggingOptions.getindex(0)).py.z()] = debug_options

        bkssystem_service = await (await self._client.symbols.objc_getClass.z("BKSSystemService")).objc_call.z("new")
        pid = (await bkssystem_service.objc_call.z("pidForApplication:", await self._client.cf.z(bundle_id))).c_int32
        if pid != -1 and kill_existing:
            logger.info(f"Kill existing process {pid}")
            await self.kill.z(pid, SIGKILL)

        await bkssystem_service.objc_call.z(
            "openApplication:options:clientPort:withResult:",
            await self._client.cf.z(bundle_id),
            await self._client.cf.z(options),
            await bkssystem_service.objc_call.z("createClientPort"),
            await self._client.get_dummy_block.z(),
        )

        start_time = datetime.now()
        while datetime.now() - start_time < timedelta(seconds=timeout):
            pid = (
                await bkssystem_service.objc_call.z("pidForApplication:", await self._client.cf.z(bundle_id))
            ).c_int32

        if pid == -1:
            raise LaunchError

        return await self.get_by_pid.z(pid)
