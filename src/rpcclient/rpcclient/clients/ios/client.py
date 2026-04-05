import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.client import AsyncDarwinClient, BaseDarwinClient, DarwinClient
from rpcclient.clients.darwin.subsystems.reports import Reports
from rpcclient.clients.darwin.symbol import AsyncDarwinSymbol, DarwinSymbol
from rpcclient.clients.ios.subsystems.accessibility import Accessibility
from rpcclient.clients.ios.subsystems.amfi import Amfi
from rpcclient.clients.ios.subsystems.backlight import Backlight
from rpcclient.clients.ios.subsystems.lockdown import Lockdown
from rpcclient.clients.ios.subsystems.mobile_gestalt import MobileGestalt
from rpcclient.clients.ios.subsystems.processes import IosProcesses
from rpcclient.clients.ios.subsystems.screen_capture import ScreenCapture
from rpcclient.clients.ios.subsystems.springboard import SpringBoard
from rpcclient.clients.ios.subsystems.telephony import Telephony
from rpcclient.clients.ios.subsystems.wifi import IosWifi
from rpcclient.core.subsystems.decorator import subsystem


CRASH_REPORTS_DIR = "Library/Logs/CrashReporter"


class BaseIosClient(BaseDarwinClient[DarwinSymbolT_co]):
    @subsystem
    def backlight(self) -> Backlight[DarwinSymbolT_co]:
        return Backlight(self)

    @subsystem
    def reports(self) -> Reports[DarwinSymbolT_co]:
        return Reports(self, CRASH_REPORTS_DIR)

    @subsystem
    def mobile_gestalt(self) -> MobileGestalt[DarwinSymbolT_co]:
        return MobileGestalt(self)

    @subsystem
    def processes(self) -> IosProcesses[DarwinSymbolT_co]:
        return IosProcesses(self)

    @subsystem
    def lockdown(self) -> Lockdown[DarwinSymbolT_co]:
        return Lockdown(self)

    @subsystem
    def telephony(self) -> Telephony[DarwinSymbolT_co]:
        return Telephony(self)

    @subsystem
    def screen_capture(self) -> ScreenCapture[DarwinSymbolT_co]:
        return ScreenCapture(self)

    @subsystem
    def accessibility(self) -> Accessibility[DarwinSymbolT_co]:
        return Accessibility(self)

    @subsystem
    def wifi(self) -> IosWifi[DarwinSymbolT_co]:
        return IosWifi(self)

    @subsystem
    def springboard(self) -> SpringBoard[DarwinSymbolT_co]:
        return SpringBoard(self)

    @subsystem
    def amfi(self) -> Amfi[DarwinSymbolT_co]:
        return Amfi(self)

    @zyncio.zmethod
    async def roots(self) -> list[str]:
        """get a list of all accessible darwin roots when used for lookup of files/preferences/..."""
        return [*(await super().roots.z()), "/var/mobile"]

    @zyncio.zproperty
    async def _airplane_mode(self) -> bool:
        # use MobileGestalt for a more accurate result
        return await type(self.mobile_gestalt).AirplaneMode(self.mobile_gestalt)

    @_airplane_mode.setter
    async def airplane_mode(self, value: bool) -> None:
        """set whether the device should enter airplane mode (turns off baseband, bt, etc...)"""
        radio_preferences = await (await self.symbols.objc_getClass.z("RadiosPreferences")).objc_call.z("new")
        await radio_preferences.objc_call.z("setAirplaneMode:", value)
        await radio_preferences.objc_call.z("synchronize")


class IosClient(BaseIosClient[DarwinSymbol], DarwinClient):
    pass


class AsyncIosClient(BaseIosClient[AsyncDarwinSymbol], AsyncDarwinClient):
    pass
