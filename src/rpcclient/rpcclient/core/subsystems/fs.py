import abc
import contextlib
import logging
import os
import posixpath
import random
import stat
import sys
import tempfile
from collections.abc import AsyncGenerator, Callable, Collection
from pathlib import Path, PurePath, PurePosixPath
from typing import TYPE_CHECKING, Any, Literal, ParamSpec, TypeVar
from typing_extensions import Buffer, Self

import zyncio

from rpcclient.clients.darwin.structs import MAXPATHLEN
from rpcclient.core._types import AsyncClientT_co, ClientBound, ClientT_co, SyncClientT_co
from rpcclient.core.allocated import Allocated
from rpcclient.core.structs.consts import (
    DT_DIR,
    DT_LNK,
    DT_REG,
    DT_UNKNOWN,
    O_CREAT,
    O_RDONLY,
    O_RDWR,
    O_TRUNC,
    O_WRONLY,
    R_OK,
    S_IFDIR,
    S_IFLNK,
    S_IFMT,
    S_IFREG,
    SEEK_CUR,
)
from rpcclient.exceptions import (
    ArgumentError,
    BadReturnValueError,
    RpcFileExistsError,
    RpcFileNotFoundError,
    RpcIsADirectoryError,
)
from rpcclient.utils import cached_async_method


if TYPE_CHECKING:
    from construct import Construct, ParsedType

    from rpcclient.core.symbol import BaseSymbol


logger = logging.getLogger(__name__)


class DirEntry(ClientBound[ClientT_co]):
    def __init__(self, path, entry, client: ClientT_co) -> None:
        self._path = path
        self._entry = entry
        self._client = client
        self._stat = None

    @property
    def name(self) -> str:
        return self._entry.d_name

    @property
    def path(self) -> str:
        return posixpath.join(self._path, self.name)

    def inode(self):
        """Return inode of the entry; cached per entry."""
        return self._entry.d_ino

    @zyncio.zmethod
    async def is_dir(self, *, follow_symlinks=True) -> bool:
        """Return True if the entry is a directory; cached per entry."""
        return await self._test_mode(follow_symlinks, S_IFDIR)

    @zyncio.zmethod
    async def is_file(self, *, follow_symlinks: bool = True):
        """Return True if the entry is a file; cached per entry."""
        return await self._test_mode(follow_symlinks, S_IFREG)

    @zyncio.zmethod
    async def is_symlink(self) -> bool:
        """Return True if the entry is a symbolic link; cached per entry."""
        if self._entry.d_type != DT_UNKNOWN:
            return self._entry.d_type == DT_LNK
        else:
            return await self._test_mode(False, S_IFLNK)

    @zyncio.zmethod
    async def stat(self, *, follow_symlinks: bool = True):
        """Return stat_result object for the entry; cached per entry."""
        if not follow_symlinks:
            return await self._get_lstat()
        if self._stat is None:
            if await self.is_symlink.z():
                self._stat = await self._fetch_stat(True)
            else:
                self._stat = await self._get_lstat()
        return self._stat

    async def _test_mode(self, follow_symlinks, mode) -> bool:
        is_symlink = self._entry.d_type == DT_LNK
        need_stat = self._entry.d_type == DT_UNKNOWN or (follow_symlinks and is_symlink)
        if not need_stat:
            d_types = {S_IFLNK: DT_LNK, S_IFDIR: DT_DIR, S_IFREG: DT_REG}
            return self._entry.d_type == d_types[mode]
        else:
            st_mode = (await self.stat.z(follow_symlinks=follow_symlinks)).st_mode
            if not st_mode:
                await self._client.raise_errno_exception.z(f"failed to stat(): {self.path}")
            return (st_mode & S_IFMT) == mode

    @cached_async_method
    async def _get_lstat(self):
        return await self._fetch_stat(False)

    async def _fetch_stat(self, follow_symlinks):
        result = self._entry.stat
        if not follow_symlinks:
            result = self._entry.lstat

        if result.errno != 0:
            await type(self._client).errno.fset(self._client, result.errno)
            await self._client.raise_errno_exception.z(f"failed to stat: {self._entry.d_name}")
        return result

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name!r}>"


class File(Allocated[ClientT_co]):
    CHUNK_SIZE = 1024 * 64

    def __init__(self, client: ClientT_co, fd: int) -> None:
        """
        :param rpcclient.client.client.Client client:
        :param fd:
        """
        super().__init__()
        self._client = client
        self.fd: int = fd

    async def _deallocate(self) -> None:
        """Close the remote file descriptor."""
        fd = (await self._client.symbols.close.z(self.fd)).c_int32
        if fd < 0:
            await self._client.raise_errno_exception.z(f"failed to close fd: {fd}")

    @zyncio.zmethod
    async def seek(self, offset: int, whence: int) -> int:
        """Seek the remote file descriptor and return the resulting offset."""
        err = (await self._client.symbols.lseek.z(self.fd, offset, whence)).c_int32
        if err < 0:
            await self._client.raise_errno_exception.z(f"failed to lseek fd: {self.fd}")
        return err

    @zyncio.zmethod
    async def tell(self) -> int:
        return await self.seek.z(0, SEEK_CUR)

    async def _write(self, buf: bytes) -> int:
        """Write bytes to the remote file descriptor."""
        n = (await self._client.symbols.write.z(self.fd, buf, len(buf))).c_int64
        if n < 0:
            await self._client.raise_errno_exception.z(f"failed to write on fd: {self.fd}")
        return n

    @zyncio.zmethod
    async def write(self, buf: bytes) -> int:
        """Write the full buffer, retrying until all bytes are written."""
        while buf:
            err = await self._write(buf)
            buf = buf[err:]
        return len(buf)

    async def _read(self, buf: "BaseSymbol", size: int) -> bytes:
        """read file at remote"""
        err = (await self._client.symbols.read.z(self.fd, buf, size)).c_int64
        if err < 0:
            await self._client.raise_errno_exception.z(f"read() failed for fd: {self.fd}")
        return await buf.peek.z(err)

    @zyncio.zmethod
    async def read_using_chunk(self, chunk: "BaseSymbol", chunk_size: int, size: int) -> bytes:
        buf = b""
        while size == -1 or len(buf) < size:
            read_chunk = await self._read(chunk, chunk_size)
            if not read_chunk:
                # EOF
                break
            buf += read_chunk
        return buf

    @zyncio.zmethod
    async def read(self, size: int = -1, chunk_size: int = CHUNK_SIZE, chunk: "BaseSymbol | None" = None) -> bytes:
        """read file at remote"""
        if size != -1 and size < chunk_size:
            chunk_size = size

        if chunk:
            return await self.read_using_chunk.z(chunk, chunk_size, size)
        else:
            async with self._client.safe_malloc.z(chunk_size) as temp_chunk:
                return await self.read_using_chunk.z(temp_chunk, chunk_size, size)

    @zyncio.zmethod
    async def pread(self, length: int, offset: int) -> bytes:
        """call pread() at remote"""
        async with self._client.safe_malloc.z(length) as buf:
            err = (await self._client.symbols.pread.z(self.fd, buf, length, offset)).c_int64
            if err < 0:
                await self._client.raise_errno_exception.z(f"pread() failed for fd: {self.fd}")
            return await buf.peek.z(err)

    @zyncio.zmethod
    async def pwrite(self, buf: bytes, offset: int) -> None:
        """call pwrite() at remote"""
        err = (await self._client.symbols.pwrite.z(self.fd, buf, len(buf), offset)).c_int64
        if err < 0:
            await self._client.raise_errno_exception.z(f"pwrite() failed for fd: {self.fd}")

    @zyncio.zmethod
    async def fdatasync(self) -> None:
        err = (await self._client.symbols.fdatasync.z(self.fd)).c_int64
        if err < 0:
            await self._client.raise_errno_exception.z(f"fdatasync() failed for fd: {self.fd}")

    @zyncio.zmethod
    async def fsync(self) -> None:
        err = (await self._client.symbols.fsync.z(self.fd)).c_int64
        if err < 0:
            await self._client.raise_errno_exception.z(f"fsync() failed for fd: {self.fd}")

    @zyncio.zmethod
    async def flock(self, operation: int) -> None:
        """Apply or clear an advisory lock on the remote file descriptor."""
        err = (await self._client.symbols.flock.z(self.fd, operation)).c_int32
        if err < 0:
            await self._client.raise_errno_exception.z(f"flock() failed for fd: {self.fd}")

    @zyncio.zmethod
    async def dup(self) -> int:
        err = (await self._client.symbols.dup.z(self.fd)).c_int64
        if err < 0:
            await self._client.raise_errno_exception.z(f"dup() failed for fd: {self.fd}")
        return err

    def __repr__(self):
        return f"<{self.__class__.__name__} FD:{self.fd}>"

    @zyncio.zmethod
    async def parse(self, struct: "Construct[ParsedType, Any]") -> "ParsedType":
        return struct.parse(await self.read.z(struct.sizeof()))


class RemotePath(PurePosixPath, ClientBound[ClientT_co]):
    def __init__(self, *args: str | os.PathLike[str], client: ClientT_co) -> None:
        if sys.version_info < (3, 12):
            super().__init__()
        else:
            super().__init__(*args)  # solution from python3.12 since signature has changed
        self._path: str = posixpath.join(*args)
        self._client = client

    if sys.version_info < (3, 12):
        # this will not be needed once python3.11 is deprecated since it is now possible to subclass normally
        def __new__(cls, *args: str | os.PathLike[str], client: ClientT_co) -> Self:
            return super().__new__(cls, *args)

        def _make_child(self, args) -> Self:
            return self.with_segments(self, *args)

    def with_segments(self, *pathsegments: str | os.PathLike[str]) -> Self:
        return type(self)(*pathsegments, client=self._client)

    @zyncio.zmethod
    async def absolute(self) -> Self:
        if self.is_absolute():
            return self
        return self.with_segments(await self._client.fs.pwd.z(), self)

    @zyncio.zmethod
    async def chmod(self, mode: int) -> None:
        return await self._client.fs.chmod.z(self._path, mode)

    @zyncio.zmethod
    async def readlink(self) -> Self:
        return self.with_segments(await self._client.fs.readlink.z(self._path))

    @zyncio.zmethod
    async def exists(self) -> bool:
        try:
            await self.stat.z()
        except Exception:
            return False
        return True

    @zyncio.zmethod
    async def is_dir(self) -> bool:
        return bool((await self.stat.z()).st_mode & S_IFDIR)

    @zyncio.zmethod
    async def lstat(self) -> Any:
        return await self._client.fs.lstat.z(self._path)

    @zyncio.zmethod
    async def mkdir(self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        await self._client.fs.mkdir.z(self._path, mode, parents=parents, exist_ok=exist_ok)

    @zyncio.zmethod
    async def read_bytes(self) -> bytes:
        async with await self._open("r") as f:
            return await f.read.z()

    @zyncio.zmethod
    async def stat(self) -> Any:
        return await self._client.fs.stat.z(self._path)

    @zyncio.zmethod
    async def symlink_to(self, target: str | PurePath, target_is_directory: Literal[False] = False) -> None:
        await self._client.fs.symlink.z(target, self._path)

    @zyncio.zmethod
    async def write_bytes(self, data: Buffer) -> int:
        async with await self._open("w") as f:
            return await f.write.z(bytes(data))

    async def _open(self, mode: str, access: int = 0o777) -> File[ClientT_co]:
        return await self._client.fs.open.z(self._path, mode, access)

    @zyncio.zgeneratormethod
    async def iterdir(self) -> AsyncGenerator[Self]:
        for entry in await self._client.fs.listdir.z(self._path):
            yield self / entry

    @zyncio.zmethod
    async def touch(self, mode: int = 438, exist_ok: bool = True) -> None:
        try:
            return await self._client.fs.touch.z(self._path, mode, exist_ok)
        except RpcFileExistsError as e:
            raise FileExistsError() from e

    @zyncio.zmethod
    async def remove(self, recursive: bool = False, force: bool = False) -> None:
        """Remove the current path from the filesystem.

        :param recursive:
        :param force:
        """
        if await self.exists.z():
            await self._client.fs.remove.z(self._path, recursive=recursive, force=force)


class RemoteTemporaryDir(RemotePath[ClientT_co]):
    """Temporary directory on the remote device"""

    _deleted: bool = False

    def __enter__(self: "RemoteTemporaryDir[SyncClientT_co]") -> "RemoteTemporaryDir[SyncClientT_co]":
        return self

    async def __aenter__(self: "RemoteTemporaryDir[AsyncClientT_co]") -> "RemoteTemporaryDir[AsyncClientT_co]":
        return self

    def __exit__(self: "RemoteTemporaryDir[SyncClientT_co]", exc_type, exc_val, exc_tb) -> None:
        self.deallocate()

    async def __aexit__(self: "RemoteTemporaryDir[AsyncClientT_co]", exc_type, exc_val, exc_tb) -> None:
        await self.deallocate()

    @zyncio.zmethod
    async def deallocate(self) -> None:
        if not self._deleted:
            await self.remove.z(recursive=True, force=True)
            self._deleted = True


_P = ParamSpec("_P")
_T_co = TypeVar("_T_co", covariant=True)


async def _do_path_op(
    op: zyncio.BoundZyncMethod[Any, _P, _T_co] | Callable[_P, _T_co], *args: _P.args, **kwargs: _P.kwargs
) -> _T_co:
    if isinstance(op, zyncio.BoundZyncMethod):
        return await op.z(*args, **kwargs)
    return op(*args, **kwargs)


class Fs(ClientBound[ClientT_co], abc.ABC):
    """filesystem utils"""

    def __init__(self, client: ClientT_co) -> None:
        self._client = client

    async def _cp_dir(
        self,
        source: Path | RemotePath[ClientT_co],
        dest: Path | RemotePath[ClientT_co],
        force: bool,
    ) -> None:
        if not await _do_path_op(dest.exists):
            await _do_path_op(dest.mkdir, (await _do_path_op(source.lstat)).st_mode)

        if isinstance(source, Path):

            async def _make_async_gen() -> AsyncGenerator[Path]:
                for file in source.iterdir():
                    yield file

            files = _make_async_gen()
        else:
            files = source.iterdir.z()

        async for src_file in files:
            dest_file = dest / src_file.name

            src_lstat = await _do_path_op(src_file.lstat)
            if stat.S_ISDIR(src_lstat.st_mode):
                await self._cp_dir(src_file, dest_file, force)
            elif stat.S_ISLNK(src_lstat.st_mode):
                symlink_full = await _do_path_op(src_file.readlink)
                await _do_path_op(dest_file.symlink_to, symlink_full)
            elif await _do_path_op(dest_file.exists) and not force:
                pass
            else:
                await _do_path_op(dest_file.write_bytes, await _do_path_op(src_file.read_bytes))

    @zyncio.zmethod
    async def cp(
        self,
        sources: Collection[Path] | Collection[RemotePath[ClientT_co]],
        dest: Path | RemotePath[ClientT_co],
        recursive: bool,
        force: bool,
    ) -> None:
        dest_exists = await _do_path_op(dest.exists)
        is_dest_dir = dest_exists and await _do_path_op(dest.is_dir)

        if (not dest_exists or not is_dest_dir) and (len(sources) > 1):
            raise ArgumentError(f"target {dest} is not a directory")

        if recursive and not dest_exists:
            try:
                await _do_path_op(dest.mkdir, 0o777)
            except Exception:
                if not await _do_path_op(dest.exists):
                    raise

        for source in sources:
            if not await _do_path_op(source.exists):
                raise ArgumentError(f"cannot stat {source}: No such file or directory")

            if await _do_path_op(source.is_dir):
                if not recursive:
                    logger.info(f"omitting directory {source}")
                else:
                    cur_dest = dest / source.name
                    source_mode = (await _do_path_op(source.stat)).st_mode
                    if not await _do_path_op(cur_dest.exists):
                        await _do_path_op(cur_dest.mkdir, source_mode)
                    await self._cp_dir(source, cur_dest, force)
            else:  # source is a file
                cur_dest = dest
                if await _do_path_op(dest.exists) and await _do_path_op(dest.is_dir):
                    cur_dest = dest / source.name
                if not await _do_path_op(cur_dest.exists) or force:
                    await _do_path_op(cur_dest.write_bytes, await _do_path_op(source.read_bytes))

    @zyncio.zmethod
    async def is_file(self, path: str | PurePath) -> bool:
        """Return True if the entry is a file"""
        return bool((await self.stat.z(path)).st_mode & S_IFREG)

    async def _chown(self, path: str | PurePath, uid: int, gid: int) -> None:
        """Change owner and group for a remote path."""
        if (await self._client.symbols.chown.z(path, uid, gid)).c_int32 < 0:
            await self._client.raise_errno_exception.z(f"failed to chown: {path}")

    @zyncio.zmethod
    async def chown(self, path: str | PurePath, uid: int, gid: int, recursive: bool = False) -> None:
        """Change owner and group for a path, optionally recursively."""
        if not recursive:
            await self._chown(path, uid, gid)
            return

        async for file in self.find.z(path, topdown=False):
            await self._chown(file, uid, gid)

    async def _chmod(self, path: str | PurePath, mode: int) -> None:
        """Change mode bits for a remote path."""
        if (await self._client.symbols.chmod.z(path, mode)).c_int32 < 0:
            await self._client.raise_errno_exception.z(f"failed to chmod: {path}")

    @zyncio.zmethod
    async def chmod(self, path: str | PurePath, mode: int, recursive: bool = False) -> None:
        """Change mode bits for a path, optionally recursively."""
        if not recursive:
            await self._chmod(path, mode)
            return

        async for file in self.find.z(path, topdown=False):
            await self._chmod(file, mode)

    async def _remove(self, path: str | PurePath, force=False) -> None:
        """Remove a file on the remote filesystem."""
        if (await self._client.symbols.remove.z(path)).c_int32 < 0 and not force:
            await self._client.raise_errno_exception.z(f"failed to remove: {path}")

    @zyncio.zmethod
    async def remove(self, path: str | PurePath, recursive: bool = False, force: bool = False) -> None:
        """Remove a file or directory tree on the remote filesystem."""
        if not recursive or await self.is_file.z(path):
            await self._remove(path, force=force)
            return

        async for filename in self.find.z(path, topdown=False):
            await self._remove(filename, force=force)

    @zyncio.zmethod
    async def rename(self, old: str | PurePath, new: str | PurePath) -> None:
        """Rename or move a path on the remote filesystem."""
        if (await self._client.symbols.rename.z(old, new)).c_int32 < 0:
            await self._client.raise_errno_exception.z(f"failed to rename: {old} -> {new}")

    async def _mkdir(self, path: str | PurePath, mode: int = 0o777) -> None:
        """Create a directory on the remote filesystem."""
        if (await self._client.symbols.mkdir.z(path, mode)).c_int64 < 0:
            await self._client.raise_errno_exception.z(f"failed to mkdir: {path}")

        # os may not always respect the permission given by the mode argument to mkdir
        await self.chmod.z(path, mode)

    @zyncio.zmethod
    async def mkdir(
        self,
        path: str | PurePath,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        """Create a directory, optionally creating parent directories."""
        if not parents:
            try:
                await self._mkdir(path, mode=mode)
            except RpcFileExistsError:
                if not exist_ok:
                    raise
            return

        dir_path = PurePosixPath(await self.pwd.z())
        for part in PurePosixPath(path).parts:
            dir_path = dir_path / part
            with contextlib.suppress(RpcIsADirectoryError, RpcFileExistsError):
                await self._mkdir(dir_path, mode=mode)

    @zyncio.zmethod
    async def chdir(self, path: str | PurePath) -> None:
        """Change the remote process working directory."""
        if (await self._client.symbols.chdir.z(path)).c_int64 < 0:
            await self._client.raise_errno_exception.z(f"failed to chdir: {path}")

    @zyncio.zmethod
    async def readlink(self, path: str | PurePath, absolute: bool = True) -> str:
        """Read the symlink target on the remote filesystem."""
        async with self._client.safe_calloc.z(MAXPATHLEN) as buf:
            if (await self._client.symbols.readlink.z(path, buf, MAXPATHLEN)).c_int64 < 0:
                await self._client.raise_errno_exception.z(f"readlink failed for: {path}")
            if absolute:
                return str(Path(path).parent / await buf.peek_str.z())
            return await buf.peek_str.z()

    @zyncio.zmethod
    async def realpath(self, path: str | PurePath) -> str:
        """Resolve a path on the remote filesystem to an absolute path."""
        async with self._client.safe_malloc.z(MAXPATHLEN) as buf:
            if await self._client.symbols.realpath.z(path, buf) == 0:
                await self._client.raise_errno_exception.z(f"realpath failed for: {path}")
            return await buf.peek_str.z()

    @zyncio.zmethod
    async def is_symlink(self, path: str | PurePath) -> bool:
        try:
            await self.readlink.z(path)
        except BadReturnValueError:
            return False
        return True

    @zyncio.zmethod
    async def open(self, file: str | PurePath, mode: str, access: int = 0o777) -> File[ClientT_co]:
        """
        call open(file, mode, access) at remote and get a context manager
        file object
        :param file: filename to be opened
        :param mode: one of:
            'r' - read only
            'r+' - read and write. exception if file doesn't exist
            'rw' - read and write. create if it doesn't exist. also truncate.
            'w' - write only. create if it doesn't exist. also truncate.
            'w+' - read and write. create if it doesn't exist.
        :param access: access mode as octal value
        :return: a context manager file object
        """
        available_modes = {
            "r": O_RDONLY,
            "r+": O_RDWR,
            "rw": O_RDWR | O_CREAT | O_TRUNC,
            "w": O_WRONLY | O_CREAT | O_TRUNC,
            "w+": O_RDWR | O_CREAT,
        }
        mode_int = available_modes.get(mode)
        if mode_int is None:
            raise ArgumentError(f"mode can be only one of: {available_modes.keys()}")

        fd = (await self._client.symbols.open.z(file, mode_int, access, va_list_index=2)).c_int32
        if fd < 0:
            await self._client.raise_errno_exception.z(f"failed to open: {file}")

        return File(self._client, fd)

    @zyncio.zmethod
    async def write_file(self, file: str | PurePath, buf: bytes, access: int = 0o777) -> None:
        async with await self.open.z(file, "w", access=access) as f:
            await f.write.z(buf)

    @zyncio.zmethod
    async def read_file(self, file: str | PurePath) -> bytes:
        async with await self.open.z(file, "r") as f:
            return await f.read.z()

    def remote_path(self, path: str | PurePath) -> RemotePath[ClientT_co]:
        return RemotePath(path, client=self._client)

    @zyncio.zmethod
    async def pull(
        self,
        remotes: list[str | PurePath] | str | PurePath,
        local: str | PurePath,
        recursive: bool = False,
        force: bool = False,
    ):
        """pull complete directory tree"""
        if not isinstance(remotes, list):
            remotes = [posixpath.expanduser(remotes)]
        remotes_str = [posixpath.expanduser(remote) for remote in remotes]
        await self.cp.z([self.remote_path(remote) for remote in remotes_str], Path(str(local)), recursive, force)

    @zyncio.zmethod
    async def push(
        self,
        local_files: list[str | PurePath] | str | PurePath,
        remote: str | PurePath,
        recursive: bool = False,
        force: bool = False,
    ):
        """push complete directory tree"""
        if not isinstance(local_files, list):
            local_files = [posixpath.expanduser(local_files)]
        locals_str = [posixpath.expanduser(local) for local in local_files]
        await self.cp.z([Path(str(local)) for local in locals_str], self.remote_path(remote), recursive, force)

    @zyncio.zmethod
    async def touch(self, file: str | PurePath, mode: int = 0o666, exist_ok: bool = True) -> None:
        """simulate unix touch command for given file"""
        if not exist_ok:
            try:
                await self.stat.z(file)
                raise RpcFileExistsError()
            except RpcFileNotFoundError:
                pass
        async with await self.open.z(file, "w+", mode):
            pass

    @zyncio.zmethod
    async def symlink(self, src: str | PurePath, dst: str | PurePath) -> int:
        """Create a symbolic link on the remote filesystem."""
        err = (await self._client.symbols.symlink.z(src, dst)).c_int64
        if err < 0:
            await self._client.raise_errno_exception.z(f"symlink failed to create link: {dst}->{src}")
        return err

    @zyncio.zmethod
    async def link(self, src: str | PurePath, dst: str | PurePath) -> int:
        """Create a hard link on the remote filesystem."""
        err = (await self._client.symbols.link.z(src, dst)).c_int64
        if err < 0:
            await self._client.raise_errno_exception.z(f"link failed to create link: {dst}->{src}")
        return err

    @zyncio.zmethod
    async def pwd(self) -> str:
        """calls getcwd(buf, size_t) and prints current path.
        with the special values NULL, 0 the buffer is allocated dynamically"""
        chunk = await self._client.symbols.getcwd.z(0, 0)
        if chunk == 0:
            await self._client.raise_errno_exception.z("getcwd() failed")
        try:
            return await chunk.peek_str.z()
        finally:
            await self._client.symbols.free.z(chunk)

    @zyncio.zmethod
    async def listdir(self, path: str | PurePath = ".") -> list[str]:
        """get directory listing for a given dirname"""
        return [e.name for e in await self.scandir.z(path)]

    @zyncio.zmethod
    async def scandir(self, path: str | PurePath = ".") -> list[DirEntry[ClientT_co]]:
        """get directory listing for a given dirname"""
        result = []
        for entry in (await self._client.listdir.z(path))[2:]:
            result.append(DirEntry(path, entry, self._client))
        return result

    @zyncio.zmethod
    @abc.abstractmethod
    async def stat(self, path: str | PurePath) -> Any:
        """Return stat info for a remote path (platform-specific implementation)."""

    @zyncio.zmethod
    @abc.abstractmethod
    async def lstat(self, path: str | PurePath) -> Any:
        """Return lstat info for a remote path (platform-specific implementation)."""

    @zyncio.zmethod
    async def accessible(self, path: str | PurePath, mode: int = R_OK) -> bool:
        """check if a given path can be accessed."""
        err = await self._client.symbols.access.z(path, mode)
        return err == 0

    @zyncio.zmethod
    async def chflags(self, path: str | PurePath, flags: int = 0) -> None:
        """set file flags"""
        err = await self._client.symbols.chflags.z(path, flags)
        if err < 0:
            await self._client.raise_errno_exception.z(f"failed to chflags on: {path}")

    @zyncio.zgeneratormethod
    async def find(self, top: str | PurePath, topdown: bool = True) -> AsyncGenerator[str]:
        """traverse a file tree top to down"""
        top = str(top)
        if topdown:
            if await self.accessible.z(top):
                yield top
            else:
                raise RpcFileNotFoundError(f"cannot access: {top}")

        async for root, dirs, files in self.walk.z(top, topdown=topdown):
            for name in files:
                yield os.path.join(root, name)
            for name in dirs:
                yield os.path.join(root, name)

        if not topdown:
            if await self.accessible.z(top):
                yield top
            else:
                raise RpcFileNotFoundError(f"cannot access: {top}")

    @zyncio.zgeneratormethod
    async def walk(
        self,
        top: str | PurePath,
        topdown: bool = True,
        onerror: Callable[[Exception], object] | None = None,
    ) -> AsyncGenerator[tuple[str, list[str], list[str]]]:
        """provides the same results as os.walk(top)"""
        top = str(top)
        dirs = []
        files = []
        try:
            for entry in await self.scandir.z(top):
                try:
                    if await entry.is_dir.z():
                        dirs.append(entry.name)
                    else:
                        files.append(entry.name)
                except Exception as e:
                    if not onerror:
                        raise
                    onerror(e)
        except Exception as e:
            if not onerror:
                raise
            onerror(e)

        if topdown:
            yield top, dirs, files

        for d in dirs:
            async for item in self.walk.z(posixpath.join(top, d), topdown=topdown, onerror=onerror):
                yield item

        if not topdown:
            yield top, dirs, files

    @zyncio.zcontextmanagermethod
    async def remote_file(self, remote: str | PurePath) -> AsyncGenerator[Path]:
        with tempfile.TemporaryDirectory() as local_dir:
            local = Path(local_dir) / PurePosixPath(remote).name
            if await self.accessible.z(remote):
                await self.pull.z(remote, local.absolute())
            try:
                yield local.absolute()
            finally:
                await self.push.z(local, remote, force=True)

    @zyncio.zmethod
    async def remote_temp_dir(
        self, directory: str | PurePath = "/tmp", mode: int = 0o700
    ) -> RemoteTemporaryDir[ClientT_co]:
        """Generate a random temp directory name and create it in the given directory (default '/tmp').

        :param directory: Directory to create the temp directory inside (default '/tmp').
        :param mode: Mode to create the temp directory with (default 0o700).
        """
        remote_dir = self.remote_path(directory)
        if not remote_dir.exists:
            raise RpcFileNotFoundError(f"remote dir {remote_dir} does not exist")

        while True:
            temp_dir = remote_dir / ("tmpdir_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789_", k=8)))
            try:
                await temp_dir.mkdir.z(mode=mode)
            except RpcFileExistsError:
                continue
            break

        return RemoteTemporaryDir(temp_dir, client=self._client)
