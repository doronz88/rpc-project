from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.clients.darwin.subsystems.reports import Reports
from rpcclient.clients.ios.subsystems.accessibility import Accessibility
from rpcclient.clients.ios.subsystems.amfi import Amfi
from rpcclient.clients.ios.subsystems.backlight import Backlight
from rpcclient.clients.ios.subsystems.lockdown import Lockdown
from rpcclient.clients.ios.subsystems.mobile_gestalt import MobileGestalt
from rpcclient.clients.ios.subsystems.processes import IosProcesses
from rpcclient.clients.ios.subsystems.screen_capture import ScreenCapture
from rpcclient.clients.ios.subsystems.sprinboard import SpringBoard
from rpcclient.clients.ios.subsystems.telephony import Telephony
from rpcclient.clients.ios.subsystems.wifi import IosWifi
from rpcclient.core.subsystems.decorator import subsystem

CRASH_REPORTS_DIR = 'Library/Logs/CrashReporter'


class IosClient(DarwinClient):

    @subsystem
    def backlight(self) -> Backlight:
        return Backlight(self)

    @subsystem
    def reports(self) -> Reports:
        return Reports(self, CRASH_REPORTS_DIR)

    @subsystem
    def mobile_gestalt(self) -> MobileGestalt:
        return MobileGestalt(self)

    @subsystem
    def processes(self) -> IosProcesses:
        return IosProcesses(self)

    @subsystem
    def lockdown(self) -> Lockdown:
        return Lockdown(self)

    @subsystem
    def telephony(self) -> Telephony:
        return Telephony(self)

    @subsystem
    def screen_capture(self) -> ScreenCapture:
        return ScreenCapture(self)

    @subsystem
    def accessibility(self) -> Accessibility:
        return Accessibility(self)

    @subsystem
    def wifi(self) -> IosWifi:
        return IosWifi(self)

    @subsystem
    def springboard(self) -> SpringBoard:
        return SpringBoard(self)

    @subsystem
    def amfi(self) -> Amfi:
        return Amfi(self)

    @property
    def roots(self) -> list[str]:
        """ get a list of all accessible darwin roots when used for lookup of files/preferences/... """
        return super().roots + ['/var/mobile']

    @property
    def airplane_mode(self) -> bool:
        # use MobileGestalt for a more accurate result
        return self.mobile_gestalt.AirplaneMode

    @airplane_mode.setter
    def airplane_mode(self, value: bool):
        """ set whether the device should enter airplane mode (turns off baseband, bt, etc...) """
        radio_preferences = self.symbols.objc_getClass('RadiosPreferences').objc_call('new')
        radio_preferences.objc_call('setAirplaneMode:', value)
        radio_preferences.objc_call('synchronize')
