import sqlite3
from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core.structs.consts import SIGKILL
from rpcclient.core.subsystems.network import Network


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient

PINNING_RULED_DB = "/private/var/protected/trustd/pinningrules.sqlite3"
SYSTEM_CONFIGURATION_PLIST = "/private/var/Managed Preferences/mobile/com.apple.SystemConfiguration.plist"


class DarwinNetwork(Network["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Network utils"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        super().__init__(client)

    async def proxy_settings(self) -> dict:
        """Get proxy settings"""
        return await (await self._client.symbols.CFNetworkCopySystemProxySettings()).py(dict)

    async def set_http_proxy(self, ip: str, port: int) -> None:
        """Set http proxy"""
        async with await self._client.preferences.sc.open(SYSTEM_CONFIGURATION_PLIST) as config:
            await config.set(
                "Proxies",
                {
                    "HTTPProxyType": 1,
                    "HTTPEnable": 1,
                    "HTTPPort": port,
                    "HTTPSProxy": ip,
                    "HTTPSPort": port,
                    "HTTPProxy": ip,
                    "HTTPSEnable": 1,
                    "BypassAllowed": 0,
                },
            )
        await (await self._client.processes.get_by_basename("configd)")).kill(SIGKILL)

    async def remove_http_proxy(self) -> None:
        """Remove http proxy settings"""
        async with await self._client.preferences.sc.open(SYSTEM_CONFIGURATION_PLIST) as config:
            await config.remove("Proxies")
        await (await self._client.processes.get_by_basename("configd")).kill(SIGKILL)

    async def remove_certificate_pinning(self) -> None:
        """Remove pinning rules from trustd"""
        async with self._client.fs.remote_file(PINNING_RULED_DB) as local_db_file:
            # truncate pinning rules
            conn = sqlite3.connect(local_db_file)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM rules")
            conn.commit()
            conn.close()

            # push new db
            await self._client.fs.push(local_db_file, PINNING_RULED_DB, force=True)

        # restart trustd for changes to take affect
        await self.kill_trustd()

    async def restore_certificate_pinning(self) -> None:
        """Restore pinning rules from trustd"""
        if await self._client.fs.accessible(PINNING_RULED_DB):
            await self._client.fs.remove(PINNING_RULED_DB)

        # Upon startup trustd to reloads pinning rules from the last MobileAsset
        await self.kill_trustd()

    async def kill_trustd(self) -> None:
        """Kill trustd processes"""
        for process in await self._client.processes.list():
            if await type(process).basename(process) == "trustd":
                await process.kill(SIGKILL)

    async def flush_dns(self) -> None:
        """Flush DNS cache"""
        await (await self._client.processes.get_by_basename("mDNSResponder")).kill(SIGKILL)
