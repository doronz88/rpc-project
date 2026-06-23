from pathlib import PurePath
from typing import TYPE_CHECKING, Generic

from construct import Container

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.structs import stat64, statfs64
from rpcclient.core.subsystems.fs import Fs


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient
    from rpcclient.clients.darwin.symbol import DarwinSymbol


async def do_stat(client: "DarwinClient[DarwinSymbol]", stat_name: str, filename: str | PurePath) -> Container:
    """Return a stat64 struct for a remote path."""
    async with client.safe_malloc(stat64.sizeof()) as buf:
        err = await client.symbols[stat_name].call(filename, buf)
        if err != 0:
            await client.raise_errno_exception(f"failed to stat(): {filename}")
        return await buf.parse(stat64)


class DarwinFs(Fs["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    async def stat(self, path: str | PurePath) -> Container:
        """Return stat64 info for a remote path."""
        return await do_stat(self._client, "stat64", path)

    async def lstat(self, path: str | PurePath) -> Container:
        """Return lstat64 info for a remote path (does not follow symlinks)."""
        return await do_stat(self._client, "lstat64", path)

    async def setxattr(self, path: str | PurePath, name: str, value: bytes) -> None:
        """set an extended attribute value"""
        count = (await self._client.symbols.setxattr(path, name, value, len(value), 0, 0)).c_int64
        if count == -1:
            await self._client.raise_errno_exception(f"failed to setxattr(): {path}")

    async def removexattr(self, path: str | PurePath, name: str) -> None:
        """remove an extended attribute value"""
        count = (await self._client.symbols.removexattr(path, name, 0)).c_int64
        if count == -1:
            await self._client.raise_errno_exception(f"failed to removexattr(): {path}")

    async def listxattr(self, path: str | PurePath) -> list[str]:
        """list extended attribute names"""
        max_buf_len = 1024
        async with self._client.safe_malloc(max_buf_len) as xattributes_names:
            count = (await self._client.symbols.listxattr(path, xattributes_names, max_buf_len, 0)).c_int64
            if count == -1:
                await self._client.raise_errno_exception(f"failed to listxattr(): {path}")
            return [s.decode() for s in (await xattributes_names.peek(count)).split(b"\x00")[:-1]]

    async def getxattr(self, path: str | PurePath, name: str) -> bytes:
        """get an extended attribute value"""
        max_buf_len = 1024
        async with self._client.safe_malloc(max_buf_len) as value:
            count = (await self._client.symbols.getxattr(path, name, value, max_buf_len, 0, 0)).c_int64
            if count == -1:
                await self._client.raise_errno_exception(f"failed to getxattr(): {path}")
            return await value.peek(count)

    async def dictxattr(self, path: str | PurePath) -> dict[str, bytes]:
        """get a dictionary of all extended attributes"""
        result = {}
        for k in await self.listxattr(path):
            result[k] = await self.getxattr(path, k)
        return result

    async def statfs(self, path: str | PurePath) -> Container:
        async with self._client.safe_malloc(statfs64.sizeof()) as buf:
            if await self._client.symbols.statfs64(path, buf) != 0:
                await self._client.raise_errno_exception(f"statfs failed for: {path}")
            return await buf.parse(statfs64)

    async def chflags(self, path: str | PurePath, flags: int = 0) -> None:
        """Set BSD file flags on a remote path."""
        if (await self._client.symbols.chflags(path, flags)) != 0:
            await self._client.raise_errno_exception(f"chflags failed for: {path}")
