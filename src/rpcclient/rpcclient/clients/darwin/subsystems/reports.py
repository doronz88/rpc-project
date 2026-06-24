from pathlib import Path
from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.subsystems.crash_reports import CrashReports
from rpcclient.core._types import ClientBound


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient


class Reports(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """equivalent to the data that can be found using the Console app inside the Reports section"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]", crash_reports_dir: str) -> None:
        self._client = client
        self.crash_reports: CrashReports[DarwinSymbolT_co] = CrashReports(client, crash_reports_dir)

    async def get_logs(self, prefix: str = "") -> list[Path]:
        result = []
        sub_paths = ["var/log", "Library/Logs"]
        for sub_path in sub_paths:
            for path in await self._client.roots():
                path = Path(path) / sub_path
                if not await self._client.fs.accessible(path):
                    continue

                async for root, _dirs, files in self._client.fs.walk(path, onerror=lambda x: None):
                    for name in files:
                        if not await self._client.fs.accessible(path):
                            continue

                        if name.endswith(".log") and name.startswith(prefix):
                            result.append(Path(root) / name)
        return result

    async def system_log(self) -> str:
        async with await self._client.fs.open("/var/log/system.log", "r") as f:
            return (await f.read()).decode()
