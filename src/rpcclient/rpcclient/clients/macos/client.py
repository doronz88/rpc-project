from rpcclient.clients.darwin.client import DarwinClient, DarwinSymbolT_co
from rpcclient.clients.darwin.subsystems.reports import Reports
from rpcclient.clients.macos.subsystems.apple_script import AppleScript
from rpcclient.core.subsystems.decorator import subsystem


CRASH_REPORTS_DIR = "Library/Logs/DiagnosticReports"


class MacosClient(DarwinClient[DarwinSymbolT_co]):
    @subsystem
    def reports(self) -> Reports:
        return Reports(self, CRASH_REPORTS_DIR)

    @subsystem
    def apple_script(self) -> AppleScript[DarwinSymbolT_co]:
        return AppleScript(self)

    async def roots(self) -> list[str]:
        """get a list of all accessible darwin roots when used for lookup of files/preferences/..."""

        result = await super().roots()
        for username in await self.fs.scandir("/Users"):
            if not await username.is_dir() or not await self.fs.accessible(username.path):
                continue
            result.append(username.path)
        return result
