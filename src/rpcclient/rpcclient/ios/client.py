import typing

from rpcclient.darwin.client import DarwinClient
from rpcclient.darwin.reports import Reports
from rpcclient.ios.accessibility import Accessibility
from rpcclient.ios.amfi import Amfi
from rpcclient.ios.backlight import Backlight
from rpcclient.ios.lockdown import Lockdown
from rpcclient.ios.mobile_gestalt import MobileGestalt
from rpcclient.ios.screen_capture import ScreenCapture
from rpcclient.ios.sprinboard import SpringBoard
from rpcclient.ios.telephony import Telephony
from rpcclient.ios.wifi import IosWifi
from rpcclient.protocol import arch_t

CRASH_REPORTS_DIR = 'Library/Logs/CrashReporter'


class IosClient(DarwinClient):
    def __init__(self, sock, sysname: str, arch: arch_t, create_socket_cb: typing.Callable):
        super().__init__(sock, sysname, arch, create_socket_cb)
        self.backlight = Backlight(self)
        self.reports = Reports(self, CRASH_REPORTS_DIR)
        self.mobile_gestalt = MobileGestalt(self)
        self.lockdown = Lockdown(self)
        self.telephony = Telephony(self)
        self.screen_capture = ScreenCapture(self)
        self.accessibility = Accessibility(self)
        self.wifi = IosWifi(self)
        self.springboard = SpringBoard(self)
        self.amfi = Amfi(self)
        self._radio_preferences = self.symbols.objc_getClass('RadiosPreferences').objc_call('new')

    @property
    def roots(self) -> typing.List[str]:
        """ get a list of all accessible darwin roots when used for lookup of files/preferences/... """
        return super().roots + ['/var/mobile']

    @property
    def airplane_mode(self) -> bool:
        # use MobileGestalt for a more accurate result
        return self.mobile_gestalt.AirplaneMode

    @airplane_mode.setter
    def airplane_mode(self, value: bool):
        """ set whether the device should enter airplane mode (turns off baseband, bt, etc...) """
        self._radio_preferences.objc_call('setAirplaneMode:', value)
        self._radio_preferences.objc_call('synchronize')
