import typing

from rpcclient.darwin.client import DarwinClient
from rpcclient.darwin.reports import Reports
from rpcclient.ios.backlight import Backlight
from rpcclient.ios.lockdown import Lockdown
from rpcclient.ios.mobile_gestalt import MobileGestalt
from rpcclient.ios.screen_capture import ScreenCapture
from rpcclient.ios.telephony import Telephony
from rpcclient.protocol import arch_t

CRASH_REPORTS_DIR = 'Library/Logs/CrashReporter'


class IosClient(DarwinClient):
    def __init__(self, sock, sysname: str, arch: arch_t, hostname: str, port: int = None):
        super().__init__(sock, sysname, arch, hostname, port)
        self.backlight = Backlight(self)
        self.reports = Reports(self, CRASH_REPORTS_DIR)
        self.mobile_gestalt = MobileGestalt(self)
        self.lockdown = Lockdown(self)
        self.telephony = Telephony(self)
        self.screen_capture = ScreenCapture(self)

    @property
    def roots(self) -> typing.List[str]:
        """ get a list of all accessible darwin roots when used for lookup of files/preferences/... """
        return super().roots + ['/var/mobile']
