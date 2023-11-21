from collections import namedtuple

from rpcclient.exceptions import RpcFailedLaunchingAppError

ScreenLockStatus = namedtuple('ScreenLockStatus', ['lock', 'passcode'])


class SpringBoard:
    def __init__(self, client):
        self._client = client

    def get_spring_board_server_port(self) -> int:
        return self._client.symbols.SBSSpringBoardServerPort()

    def launch_application(self, bundle_identifier: str) -> None:
        """ launch application using SpringBoardServices """
        err = self._client.symbols.SBSLaunchApplicationWithIdentifier(self._client.cf(bundle_identifier), 0)
        if err != 0:
            raise RpcFailedLaunchingAppError(
                f'SBSLaunchApplicationWithIdentifier failed with: error code {err} - '
                f'{self._client.symbols.SBSApplicationLaunchingErrorString(err).py()}')

    def get_screen_lock_status(self) -> ScreenLockStatus:
        """ get lockscreen and passcode status using SpringBoardServices """
        server_port = self.get_spring_board_server_port()
        with self._client.safe_malloc(8) as p_is_lock:
            with self._client.safe_malloc(8) as p_is_passcode:
                p_is_lock[0] = 0
                p_is_passcode[0] = 0
                self._client.symbols.SBGetScreenLockStatus(server_port, p_is_lock, p_is_passcode)
                return ScreenLockStatus(p_is_lock[0] == 1, p_is_passcode[0] == 1)

    def open_sensitive_url_and_unlock(self, url: str, unlock: bool = True) -> None:
        """ open default application according to url scheme """
        screen_lock_status = self.get_screen_lock_status()
        if not unlock and screen_lock_status.lock:
            if screen_lock_status.passcode:
                raise RpcFailedLaunchingAppError(
                    'cannot open url while screen is locked with passcode. you must unlock device first')
            raise RpcFailedLaunchingAppError('cannot open url while screen is locked, use unlock=True parameter')
        cf_url_ref = self._client.symbols.objc_getClass('NSURL').objc_call('URLWithString:', self._client.cf(url))
        if not self._client.symbols.SBSOpenSensitiveURLAndUnlock(cf_url_ref, unlock):
            raise RpcFailedLaunchingAppError('SBSOpenSensitiveURLAndUnlock failed')
