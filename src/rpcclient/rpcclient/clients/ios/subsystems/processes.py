import logging
from datetime import datetime, timedelta
from typing import Optional

from rpcclient.clients.darwin.subsystems.processes import DarwinProcesses, Process
from rpcclient.core.structs.consts import SIGKILL
from rpcclient.exceptions import LaunchError

logger = logging.getLogger(__name__)


class IosProcesses(DarwinProcesses):
    def launch(self, bundle_id: str, kill_existing: bool = True, timeout: float = 1, unlock_device: bool = True,
               disable_aslr: bool = False, wait_for_debugger: bool = False, stdout: Optional[str] = None,
               stderr: Optional[str] = None) -> Process:
        """
        launch process using BackBoardService
        https://github.com/swigger/debugserver-ios/blob/master/inc/BackBoardServices.framework/Headers/BackBoardServices.h
        """
        debug_options = {}
        options = {}
        sym = self._client.symbols
        debug_options[sym.BKSDebugOptionKeyDisableASLR[0].py()] = disable_aslr
        debug_options[sym.BKSDebugOptionKeyWaitForDebugger[0].py()] = wait_for_debugger
        if stdout is not None:
            debug_options[sym.BKSDebugOptionKeyStandardOutPath[0].py()] = stdout
        if stderr is not None:
            debug_options[sym.BKSDebugOptionKeyStandardErrorPath[0].py()] = stderr
        options[sym.BKSOpenApplicationOptionKeyUnlockDevice[0].py()] = unlock_device
        options[sym.BKSOpenApplicationOptionKeyDebuggingOptions[0].py()] = debug_options

        bkssystem_service = self._client.symbols.objc_getClass('BKSSystemService').objc_call('new')
        pid = bkssystem_service.objc_call('pidForApplication:', self._client.cf(bundle_id)).c_int32
        if pid != -1 and kill_existing:
            logger.info(f'Kill existing process {pid}')
            self.kill(pid, SIGKILL)

        bkssystem_service.objc_call(
            'openApplication:options:clientPort:withResult:', self._client.cf(bundle_id), self._client.cf(options),
            bkssystem_service.objc_call('createClientPort'), self._client.get_dummy_block())

        start_time = datetime.now()
        timeout = timedelta(seconds=timeout)
        while datetime.now() - start_time < timeout:
            pid = bkssystem_service.objc_call('pidForApplication:', self._client.cf(bundle_id)).c_int32

        if pid == -1:
            raise LaunchError()
        return self.get_by_pid(pid)
