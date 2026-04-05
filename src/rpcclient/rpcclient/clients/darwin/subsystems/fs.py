from pathlib import PurePath
from typing import TYPE_CHECKING, Generic

import zyncio
from construct import Container

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.structs import stat64, statfs64
from rpcclient.core.subsystems.fs import Fs


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient
    from rpcclient.clients.darwin.symbol import BaseDarwinSymbol


@zyncio.zfunc
async def do_stat(
    zync_mode: zyncio.Mode, client: "BaseDarwinClient[BaseDarwinSymbol]", stat_name: str, filename: str | PurePath
) -> Container:
    """Return a stat64 struct for a remote path."""
    async with client.safe_malloc.z(stat64.sizeof()) as buf:
        err = await client.symbols[stat_name].call(filename, buf)
        if err != 0:
            await client.raise_errno_exception.z(f"failed to stat(): {filename}")
        return await buf.parse.z(stat64)


class DarwinFs(Fs["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    @zyncio.zmethod
    async def stat(self, path: str | PurePath) -> Container:
        """Return stat64 info for a remote path."""
        return await do_stat[self._client.__zync_mode__](self._client, "stat64", path)

    @zyncio.zmethod
    async def lstat(self, path: str | PurePath) -> Container:
        """Return lstat64 info for a remote path (does not follow symlinks)."""
        return await do_stat[self._client.__zync_mode__](self._client, "lstat64", path)

    @zyncio.zmethod
    async def setxattr(self, path: str | PurePath, name: str, value: bytes) -> None:
        """set an extended attribute value"""
        count = (await self._client.symbols.setxattr.z(path, name, value, len(value), 0, 0)).c_int64
        if count == -1:
            await self._client.raise_errno_exception.z(f"failed to setxattr(): {path}")

    @zyncio.zmethod
    async def removexattr(self, path: str | PurePath, name: str) -> None:
        """remove an extended attribute value"""
        count = (await self._client.symbols.removexattr.z(path, name, 0)).c_int64
        if count == -1:
            await self._client.raise_errno_exception.z(f"failed to removexattr(): {path}")

    @zyncio.zmethod
    async def listxattr(self, path: str | PurePath) -> list[str]:
        """list extended attribute names"""
        max_buf_len = 1024
        async with self._client.safe_malloc.z(max_buf_len) as xattributes_names:
            count = (await self._client.symbols.listxattr.z(path, xattributes_names, max_buf_len, 0)).c_int64
            if count == -1:
                await self._client.raise_errno_exception.z(f"failed to listxattr(): {path}")
            return [s.decode() for s in (await xattributes_names.peek.z(count)).split(b"\x00")[:-1]]

    @zyncio.zmethod
    async def getxattr(self, path: str | PurePath, name: str) -> bytes:
        """get an extended attribute value"""
        max_buf_len = 1024
        async with self._client.safe_malloc.z(max_buf_len) as value:
            count = (await self._client.symbols.getxattr.z(path, name, value, max_buf_len, 0, 0)).c_int64
            if count == -1:
                await self._client.raise_errno_exception.z(f"failed to getxattr(): {path}")
            return await value.peek.z(count)

    @zyncio.zmethod
    async def dictxattr(self, path: str | PurePath) -> dict[str, bytes]:
        """get a dictionary of all extended attributes"""
        result = {}
        for k in await self.listxattr.z(path):
            result[k] = await self.getxattr.z(path, k)
        return result

    @zyncio.zmethod
    async def statfs(self, path: str | PurePath) -> Container:
        async with self._client.safe_malloc.z(statfs64.sizeof()) as buf:
            if await self._client.symbols.statfs64.z(path, buf) != 0:
                await self._client.raise_errno_exception.z(f"statfs failed for: {path}")
            return await buf.parse.z(statfs64)

    @zyncio.zmethod
    async def chflags(self, path: str | PurePath, flags: int = 0) -> None:
        """Set BSD file flags on a remote path."""
        if (await self._client.symbols.chflags.z(path, flags)) != 0:
            await self._client.raise_errno_exception.z(f"chflags failed for: {path}")
