from typing import Optional

from rpcclient.darwin.processes import DarwinProcesses
from rpcclient.exceptions import LaunchError


class IosProcesses(DarwinProcesses):

    def launch(self, bundle_id: str, unlock_device: bool = True, disable_aslr: bool = False,
               wait_for_debugger: bool = False, stdout: Optional[str] = None,
               stderr: Optional[str] = None) -> int:
        """ launch process using BackBoardService
        https://github.com/swigger/debugserver-ios/blob/master/inc/BackBoardServices.framework/Headers
        /BackBoardServices.h"""
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

        bkssystem_service = self._client.objc_get_class('BKSSystemService').new().objc_symbol
        bkssystem_service.openApplication_options_clientPort_withResult_(self._client.cf(bundle_id),
                                                                         self._client.cf(options),
                                                                         bkssystem_service.createClientPort(),
                                                                         self._client.get_dummy_block())

        pid = bkssystem_service.pidForApplication_(self._client.cf(bundle_id)).c_int32
        if pid == -1:
            raise LaunchError()
        return pid
