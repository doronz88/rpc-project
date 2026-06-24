from pathlib import Path
from typing import TYPE_CHECKING, Generic

from pycrashreport.crash_report import CrashReportBase, get_crash_report_from_buf

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient


class CrashReports(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """ " manage crash reports"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]", crash_reports_dir: str) -> None:
        self._client = client
        self._crash_reports_dir: str = crash_reports_dir

    async def set_symbolicated(self, enabled: bool = True) -> None:
        """
        enable/disable crash reports symbolication
        https://github.com/dlevi309/Symbolicator
        """
        await self._client.preferences.cf.set("SymbolicateCrashes", enabled, "com.apple.CrashReporter", "root")

        # bugfix: at some point, this setting was moved to "com.apple.osanalytics" bundle identifier
        await self._client.preferences.cf.set("SymbolicateCrashes", enabled, "com.apple.osanalytics", "root")

    async def list(self, prefixed: str = "") -> list[CrashReportBase]:
        """get a list of all crash reports as CrashReport parsed objects"""
        result = []
        for root in await self._client.roots():
            root = Path(root) / self._crash_reports_dir

            if not await self._client.fs.accessible(root):
                continue

            for entry in await self._client.fs.scandir(root):
                if await entry.is_file() and entry.name.endswith(".ips") and entry.name.startswith(prefixed):
                    async with await self._client.fs.open(entry.path, "r") as f:
                        result.append(get_crash_report_from_buf((await f.read()).decode(), filename=entry.path))
        return result

    async def clear(self, prefixed: str = "") -> None:
        """remove all existing crash reports"""
        for entry in await self.list(prefixed=prefixed):
            await self._client.fs.remove(entry.filename)
