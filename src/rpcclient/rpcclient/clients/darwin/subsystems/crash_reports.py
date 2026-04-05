from pathlib import Path
from typing import TYPE_CHECKING, Generic

import zyncio
from pycrashreport.crash_report import CrashReportBase, get_crash_report_from_buf

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient


class CrashReports(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """ " manage crash reports"""

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]", crash_reports_dir: str) -> None:
        self._client = client
        self._crash_reports_dir: str = crash_reports_dir

    @zyncio.zmethod
    async def set_symbolicated(self, enabled: bool = True) -> None:
        """
        enable/disable crash reports symbolication
        https://github.com/dlevi309/Symbolicator
        """
        await self._client.preferences.cf.set.z("SymbolicateCrashes", enabled, "com.apple.CrashReporter", "root")

        # bugfix: at some point, this setting was moved to "com.apple.osanalytics" bundle identifier
        await self._client.preferences.cf.set.z("SymbolicateCrashes", enabled, "com.apple.osanalytics", "root")

    @zyncio.zmethod
    async def list(self, prefixed: str = "") -> list[CrashReportBase]:
        """get a list of all crash reports as CrashReport parsed objects"""
        result = []
        for root in await self._client.roots.z():
            root = Path(root) / self._crash_reports_dir

            if not await self._client.fs.accessible.z(root):
                continue

            for entry in await self._client.fs.scandir.z(root):
                if await entry.is_file.z() and entry.name.endswith(".ips") and entry.name.startswith(prefixed):
                    async with await self._client.fs.open.z(entry.path, "r") as f:
                        result.append(get_crash_report_from_buf((await f.read.z()).decode(), filename=entry.path))
        return result

    @zyncio.zmethod
    async def clear(self, prefixed: str = "") -> None:
        """remove all existing crash reports"""
        for entry in await self.list.z(prefixed=prefixed):
            await self._client.fs.remove.z(entry.filename)
