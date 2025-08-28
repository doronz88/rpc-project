import contextlib
import logging
import os
import posixpath
import stat
import tempfile
from collections.abc import Generator
from pathlib import Path, PosixPath
from random import Random
from typing import Union

from parameter_decorators import path_to_str

from rpcclient.clients.darwin.structs import MAXPATHLEN
from rpcclient.clients.darwin.symbol import DarwinSymbol
from rpcclient.core.allocated import Allocated
from rpcclient.core.structs.consts import DT_DIR, DT_LNK, DT_REG, DT_UNKNOWN, O_CREAT, O_RDONLY, O_RDWR, O_TRUNC, \
    O_WRONLY, R_OK, S_IFDIR, S_IFLNK, S_IFMT, S_IFREG, SEEK_CUR
from rpcclient.exceptions import ArgumentError, BadReturnValueError, RpcFileExistsError, RpcFileNotFoundError, \
    RpcIsADirectoryError

logger = logging.getLogger(__name__)


class DirEntry:
    def __init__(self, path, entry, client):
        self._path = path
        self._entry = entry
        self._client = client
        self._lstat = None
        self._stat = None

    @property
    def name(self) -> str:
        return self._entry.d_name

    @property
    def path(self) -> str:
        return posixpath.join(self._path, self.name)

    def inode(self):
        """ Return inode of the entry; cached per entry. """
        return self._entry.d_ino

    def is_dir(self, *, follow_symlinks=True):
        """ Return True if the entry is a directory; cached per entry. """
        return self._test_mode(follow_symlinks, S_IFDIR)

    def is_file(self, *, follow_symlinks=True):
        """ Return True if the entry is a file; cached per entry. """
        return self._test_mode(follow_symlinks, S_IFREG)

    def is_symlink(self):
        """ Return True if the entry is a symbolic link; cached per entry. """
        if self._entry.d_type != DT_UNKNOWN:
            return self._entry.d_type == DT_LNK
        else:
            return self._test_mode(False, S_IFLNK)

    def stat(self, *, follow_symlinks=True):
        """ Return stat_result object for the entry; cached per entry. """
        if not follow_symlinks:
            return self._get_lstat()
        if self._stat is None:
            if self.is_symlink():
                self._stat = self._fetch_stat(True)
            else:
                self._stat = self._get_lstat()
        return self._stat

    def _test_mode(self, follow_symlinks, mode):
        is_symlink = self._entry.d_type == DT_LNK
        need_stat = self._entry.d_type == DT_UNKNOWN or (follow_symlinks and is_symlink)
        if not need_stat:
            d_types = {S_IFLNK: DT_LNK, S_IFDIR: DT_DIR, S_IFREG: DT_REG}
            return self._entry.d_type == d_types[mode]
        else:
            st_mode = self.stat(follow_symlinks=follow_symlinks).st_mode
            if not st_mode:
                self._client.raise_errno_exception(f'failed to stat(): {self.path}')
            return (st_mode & S_IFMT) == mode

    def _get_lstat(self):
        if self._lstat is None:
            self._lstat = self._fetch_stat(False)
        return self._lstat

    def _fetch_stat(self, follow_symlinks):
        result = self._entry.stat
        if not follow_symlinks:
            result = self._entry.lstat

        if result.errno != 0:
            self._client.errno = result.errno
            self._client.raise_errno_exception(f'failed to stat: {self._entry.d_name}')
        return result

    def __repr__(self):
        return f'<{self.__class__.__name__} NAME:{self.name}{"/" if self.is_dir() else ""}>'


class File(Allocated):
    CHUNK_SIZE = 1024 * 64

    def __init__(self, client, fd: int):
        """
        :param rpcclient.client.client.Client client:
        :param fd:
        """
        super().__init__()
        self._client = client
        self.fd = fd

    def _deallocate(self):
        """ close(fd) at remote. read man for more details. """
        fd = self._client.symbols.close(self.fd).c_int32
        if fd < 0:
            self._client.raise_errno_exception(f'failed to close fd: {fd}')

    def seek(self, offset: int, whence: int) -> int:
        """ lseek(fd, offset, whence) at remote. read man for more details. """
        err = self._client.symbols.lseek(self.fd, offset, whence).c_int32
        if err < 0:
            self._client.raise_errno_exception(f'failed to lseek fd: {self.fd}')
        return err

    def tell(self) -> int:
        return self.seek(0, SEEK_CUR)

    def _write(self, buf: bytes) -> int:
        """ write(fd, buf, size) at remote. read man for more details. """
        n = self._client.symbols.write(self.fd, buf, len(buf)).c_int64
        if n < 0:
            self._client.raise_errno_exception(f'failed to write on fd: {self.fd}')
        return n

    def write(self, buf: bytes) -> int:
        """ continue call write() until """
        while buf:
            err = self._write(buf)
            buf = buf[err:]
        return len(buf)

    def _read(self, buf: DarwinSymbol, size: int) -> bytes:
        """ read file at remote """
        err = self._client.symbols.read(self.fd, buf, size).c_int64
        if err < 0:
            self._client.raise_errno_exception(f'read() failed for fd: {self.fd}')
        return buf.peek(err)

    def read_using_chunk(self, chunk: DarwinSymbol, chunk_size: int, size: int) -> bytes:
        buf = b''
        while size == -1 or len(buf) < size:
            read_chunk = self._read(chunk, chunk_size)
            if not read_chunk:
                # EOF
                break
            buf += read_chunk
        return buf

    def read(self, size: int = -1, chunk_size: int = CHUNK_SIZE, chunk: DarwinSymbol = None) -> bytes:
        """ read file at remote """
        if size != -1 and size < chunk_size:
            chunk_size = size

        buf = b''
        if chunk:
            return self.read_using_chunk(chunk, chunk_size, size)
        else:
            with self._client.safe_malloc(chunk_size) as temp_chunk:
                return self.read_using_chunk(temp_chunk, chunk_size, size)
        return buf

    def pread(self, length: int, offset: int) -> bytes:
        """ call pread() at remote """
        with self._client.safe_malloc(length) as buf:
            err = self._client.symbols.pread(self.fd, buf, length, offset).c_int64
            if err < 0:
                self._client.raise_errno_exception(f'pread() failed for fd: {self.fd}')
            return buf.peek(err)

    def pwrite(self, buf: bytes, offset: int):
        """ call pwrite() at remote """
        err = self._client.symbols.pwrite(self.fd, buf, len(buf), offset).c_int64
        if err < 0:
            self._client.raise_errno_exception(f'pwrite() failed for fd: {self.fd}')

    def fdatasync(self):
        err = self._client.symbols.fdatasync(self.fd).c_int64
        if err < 0:
            self._client.raise_errno_exception(f'fdatasync() failed for fd: {self.fd}')

    def fsync(self):
        err = self._client.symbols.fsync(self.fd).c_int64
        if err < 0:
            self._client.raise_errno_exception(f'fsync() failed for fd: {self.fd}')

    def dup(self) -> int:
        err = self._client.symbols.dup(self.fd).c_int64
        if err < 0:
            self._client.raise_errno_exception(f'dup() failed for fd: {self.fd}')
        return err

    def __repr__(self):
        return f'<{self.__class__.__name__} FD:{self.fd}>'


class RemotePath(PosixPath):
    def __init__(self, path: str, client) -> None:
        try:
            super().__init__(path)  # solution from python3.12 since signature has changed
        except TypeError:
            super().__init__()
        self._path = path
        self._client = client

    def __new__(cls, path: str, client):
        # this will not be needed once python3.11 is deprecated since it is now possible to subclass normally
        return super().__new__(cls, *[path])

    def chmod(self, mode: int):
        return self._client.fs.chmod(self._path, mode)

    def readlink(self):
        return self._client.fs.readlink(self._path)

    def exists(self) -> bool:
        try:
            self.stat()
            return True
        except Exception:
            return False

    def is_dir(self) -> bool:
        return bool(self.stat().st_mode & S_IFDIR)

    def lstat(self):
        return self._client.fs.lstat(self._path)

    def mkdir(self, mode: int, exist_ok=False):
        self._client.fs.mkdir(self._path, mode, exist_ok)

    def read_bytes(self) -> bytes:
        with self._open('r') as f:
            return f.read()

    def stat(self):
        return self._client.fs.stat(self._path)

    def symlink_to(self, target: Path, target_is_directory: bool = False) -> None:
        return self._client.fs.symlink(target, self._path)

    def write_bytes(self, buf: bytes) -> int:
        with self._open('w') as f:
            return f.write(buf)

    def _open(self, mode: str, access: int = 0o777) -> File:
        return self._client.fs.open(self._path, mode, access)

    def iterdir(self) -> Generator['RemotePath', None, None]:
        for entry in self._client.fs.listdir(self._path):
            yield self.__class__(f'{self._path}/{entry}', self._client)

    def touch(self, mode: int = 438, exist_ok: bool = True) -> None:
        try:
            return self._client.fs.touch(self._path, mode, exist_ok)
        except RpcFileExistsError:
            raise FileExistsError()

    def __truediv__(self, key: Path) -> 'RemotePath':
        return RemotePath(f'{self._path}/{key}', self._client)

    def remove(self, recursive: bool = False, force: bool = False):
        """Remove the current path from the filesystem.

        :param recursive:
        :param force:
        """
        if self.exists():
            self._client.fs.remove(self._path, recursive=recursive, force=force)


class RemoteTemporaryDir(Allocated, RemotePath):
    """ Temporary directory on the remote device """

    def __init__(self, client, directory: str = '/tmp', mode: int = 0o700):
        """Generate a random temp directory name and create it in the given directory (default '/tmp').

        :param rpcclient.darwin.client.DarwinClient client:
        :param directory: Directory to create the temp directory inside (default '/tmp').
        :param mode: Mode to create the temp directory with (default 0o700).
        """
        Allocated.__init__(self)
        remote_dir = client.fs.remote_path(directory)
        if not remote_dir.exists:
            raise RpcFileNotFoundError(f'remote dir {remote_dir} does not exist')
        name = 'tmpdir_' + ''.join(Random().choices('abcdefghijklmnopqrstuvwxyz0123456789_', k=8))
        remote_path = client.fs.remote_path(str(remote_dir / Path(name)))
        RemotePath.__init__(self, remote_path, client)
        self.mkdir(mode)

    def __new__(cls, *args, **kwargs):
        # this will not be needed once python3.11 is deprecated since it is now possible to subclass normally
        return RemotePath.__new__(cls, *[args[1], args[0]])

    def _deallocate(self):
        """Remove the temp directory from the filesystem recursively"""
        self.remove(recursive=True, force=True)


class Fs:
    """ filesystem utils """

    def __init__(self, client):
        self._client = client

    def _cp_dir(self, source: Path, dest: Path, force: bool):
        if not dest.exists():
            dest.mkdir(source.lstat().st_mode)

        files = source.iterdir()

        for src_file in files:
            dest_file = dest / src_file.name

            src_lstat = src_file.lstat()
            if stat.S_ISDIR(src_lstat.st_mode):
                self._cp_dir(src_file, dest_file, force)
            elif stat.S_ISLNK(src_lstat.st_mode):
                symlink_full = src_file.readlink()
                dest_file.symlink_to(symlink_full)
            elif dest_file.exists() and not force:
                pass
            else:
                dest_file.write_bytes(src_file.read_bytes())

    def cp(self, sources: list[Path], dest: Path, recursive: bool, force: bool):
        dest_exists = dest.exists()
        is_dest_dir = dest_exists and dest.is_dir()

        if (not dest_exists or not is_dest_dir) and (len(sources) > 1):
            raise ArgumentError(f'target {dest} is not a directory')

        if recursive:
            if not dest_exists:
                try:
                    dest.mkdir(0o777)
                except Exception as e:
                    if not dest.exists():
                        raise e

        for source in sources:
            if not source.exists():
                raise ArgumentError(f'cannot stat {source}: No such file or directory')

            if source.is_dir():
                if not recursive:
                    logger.info(f'omitting directory {source}')
                else:
                    cur_dest = dest / source.name
                    source_mode = source.stat().st_mode
                    if not cur_dest.exists():
                        cur_dest.mkdir(source_mode)
                    self._cp_dir(source, cur_dest, force)
            else:  # source is a file
                cur_dest = dest
                if dest.exists() and dest.is_dir():
                    cur_dest = dest / source.name
                if not cur_dest.exists() or force:
                    cur_dest.write_bytes(source.read_bytes())

    @path_to_str('path')
    def is_file(self, path: str) -> bool:
        """ Return True if the entry is a file """
        return bool(self.stat(path).st_mode & S_IFREG)

    @path_to_str('path')
    def _chown(self, path: str, uid: int, gid: int):
        """ chmod(path, mode) at remote. read man for more details. """
        if self._client.symbols.chown(path, uid, gid).c_int32 < 0:
            self._client.raise_errno_exception(f'failed to chown: {path}')

    @path_to_str('path')
    def chown(self, path: str, uid: int, gid: int, recursive=False):
        """ chmod(path, mode) at remote. read man for more details. """
        if not recursive:
            self._chown(path, uid, gid)
            return

        for file in self.find(path, topdown=False):
            self._chown(file, uid, gid)

    @path_to_str('path')
    def _chmod(self, path: str, mode: int):
        """ chmod(path, mode) at remote. read man for more details. """
        if self._client.symbols.chmod(path, mode).c_int32 < 0:
            self._client.raise_errno_exception(f'failed to chmod: {path}')

    @path_to_str('path')
    def chmod(self, path: str, mode: int, recursive=False):
        """ chmod(path, mode) at remote. read man for more details. """
        if not recursive:
            self._chmod(path, mode)
            return

        for file in self.find(path, topdown=False):
            self._chmod(file, mode)

    @path_to_str('path')
    def _remove(self, path: str, force=False):
        """ remove(path) at remote. read man for more details. """
        if self._client.symbols.remove(path).c_int32 < 0:
            if not force:
                self._client.raise_errno_exception(f'failed to remove: {path}')

    @path_to_str('path')
    def remove(self, path: str, recursive=False, force=False):
        """ remove(path) at remote. read man for more details. """
        if not recursive or self.is_file(path):
            self._remove(path, force=force)
            return

        for filename in self.find(path, topdown=False):
            self._remove(filename, force=force)

    @path_to_str('old')
    @path_to_str('new')
    def rename(self, old: str, new: str):
        """ rename(old, new) at remote. read man for more details. """
        if self._client.symbols.rename(old, new).c_int32 < 0:
            self._client.raise_errno_exception(f'failed to rename: {old} -> {new}')

    @path_to_str('path')
    def _mkdir(self, path: str, mode: int = 0o777):
        """ mkdir(path, mode) at remote. read man for more details. """
        if self._client.symbols.mkdir(path, mode).c_int64 < 0:
            self._client.raise_errno_exception(f'failed to mkdir: {path}')

        # os may not always respect the permission given by the mode argument to mkdir
        self.chmod(path, mode)

    @path_to_str('path')
    def mkdir(self, path: str, mode: int = 0o777, parents=False, exist_ok=False):
        """ mkdir(path, mode) at remote. read man for more details. """
        if not parents:
            try:
                self._mkdir(path, mode=mode)
            except RpcFileExistsError:
                if not exist_ok:
                    raise
            return

        dir_path = Path(self.pwd())
        for part in Path(path).parts:
            dir_path = dir_path / part
            try:
                self._mkdir(dir_path, mode=mode)
            except (RpcIsADirectoryError, RpcFileExistsError):
                pass

    @path_to_str('path')
    def chdir(self, path: str):
        """ chdir(path) at remote. read man for more details. """
        if self._client.symbols.chdir(path).c_int64 < 0:
            self._client.raise_errno_exception(f'failed to chdir: {path}')

    @path_to_str('path')
    def readlink(self, path: str, absolute=True) -> str:
        """ readlink() at remote. read man for more details. """
        with self._client.safe_calloc(MAXPATHLEN) as buf:
            if self._client.symbols.readlink(path, buf, MAXPATHLEN).c_int64 < 0:
                self._client.raise_errno_exception(f'readlink failed for: {path}')
            if absolute:
                return str(Path(path).parent / buf.peek_str())
            return buf.peek_str()

    @path_to_str('path')
    def realpath(self, path: str) -> str:
        """ realpath() at remote. read man for more details. """
        with self._client.safe_malloc(MAXPATHLEN) as buf:
            if self._client.symbols.realpath(path, buf) == 0:
                self._client.raise_errno_exception(f'realpath failed for: {path}')
            return buf.peek_str()

    @path_to_str('path')
    def is_symlink(self, path: str) -> bool:
        try:
            self.readlink(path)
            return True
        except BadReturnValueError:
            return False

    @path_to_str('file')
    def open(self, file: str, mode: str, access: int = 0o777) -> File:
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
            'r': O_RDONLY,
            'r+': O_RDWR,
            'rw': O_RDWR | O_CREAT | O_TRUNC,
            'w': O_WRONLY | O_CREAT | O_TRUNC,
            'w+': O_RDWR | O_CREAT,
        }
        mode_int = available_modes.get(mode)
        if mode_int is None:
            raise ArgumentError(f'mode can be only one of: {available_modes.keys()}')

        fd = self._client.symbols.open(file, mode_int, access, va_list_index=2).c_int32
        if fd < 0:
            self._client.raise_errno_exception(f'failed to open: {file}')

        return File(self._client, fd)

    @path_to_str('file')
    def write_file(self, file: str, buf: bytes, access: int = 0o777):
        with self.open(file, 'w', access=access) as f:
            f.write(buf)

    @path_to_str('file')
    def read_file(self, file: str) -> bytes:
        with self.open(file, 'r') as f:
            return f.read()

    def remote_path(self, path: str) -> RemotePath:
        return RemotePath(path, self._client)

    @path_to_str('local')
    def pull(self, remotes: Union[list[Union[str, Path]], Union[str, Path]], local: str, recursive: bool = False,
             force: bool = False):
        """ pull complete directory tree """
        if not isinstance(remotes, list):
            remotes = [posixpath.expanduser(remotes)]
        remotes_str = [posixpath.expanduser(remote) for remote in remotes]
        self.cp([self.remote_path(remote) for remote in remotes_str], Path(str(local)), recursive, force)

    @path_to_str('remote')
    def push(self, locals: Union[list[Union[str, Path]], Union[str, Path]], remote: str, recursive: bool = False,
             force: bool = False):
        """ push complete directory tree """
        if not isinstance(locals, list):
            locals = [posixpath.expanduser(locals)]
        locals_str = [posixpath.expanduser(local) for local in locals]
        self.cp([Path(str(local)) for local in locals_str], self.remote_path(remote), recursive, force)

    @path_to_str('file')
    def touch(self, file: str, mode: int = 0o666, exist_ok=True):
        """ simulate unix touch command for given file """
        if not exist_ok:
            try:
                self.stat(file)
                raise RpcFileExistsError()
            except RpcFileNotFoundError:
                pass
        with self.open(file, 'w+', mode):
            pass

    @path_to_str('src', 'dst')
    def symlink(self, src: str, dst: str) -> int:
        """ symlink(src, dst) at remote. read man for more details. """
        err = self._client.symbols.symlink(src, dst).c_int64
        if err < 0:
            self._client.raise_errno_exception(
                f'symlink failed to create link: {dst}->{src}')
        return err

    @path_to_str('src', 'dst')
    def link(self, src: str, dst: str) -> int:
        """ link(src, dst) - hardlink at remote. read man for more details. """
        err = self._client.symbols.link(src, dst).c_int64
        if err < 0:
            self._client.raise_errno_exception(f'link failed to create link: {dst}->{src}')
        return err

    def pwd(self) -> str:
        """ calls getcwd(buf, size_t) and prints current path.
            with the special values NULL, 0 the buffer is allocated dynamically """
        chunk = self._client.symbols.getcwd(0, 0)
        if chunk == 0:
            self._client.raise_errno_exception('getcwd() failed')
        buf = chunk.peek_str()
        self._client.symbols.free(chunk)
        return buf

    @path_to_str('path')
    def listdir(self, path: str = '.') -> list[str]:
        """ get directory listing for a given dirname """
        return [e.name for e in self.scandir(path)]

    @path_to_str('path')
    def scandir(self, path: str = '.') -> list[DirEntry]:
        """ get directory listing for a given dirname """
        result = []
        for entry in self._client.listdir(path)[2:]:
            result.append(DirEntry(path, entry, self._client))
        return result

    @path_to_str('path')
    def stat(self, path: str):
        """ stat(filename) at remote. read man for more details. """
        raise NotImplementedError()

    @path_to_str('path')
    def lstat(self, path: str):
        """ lstat(filename) at remote. read man for more details. """
        raise NotImplementedError()

    @path_to_str('path')
    def accessible(self, path: str, mode: int = R_OK):
        """ check if a given path can be accessed. """
        err = self._client.symbols.access(path, mode)
        return err == 0

    @path_to_str('path')
    def chflags(self, path: str, flags: int = 0):
        """ set file flags """
        err = self._client.symbols.chflags(path, flags)
        if err < 0:
            self._client.raise_errno_exception(f'failed to chflags on: {path}')

    @path_to_str('top')
    def find(self, top: str, topdown=True):
        """ traverse a file tree top to down """
        if topdown:
            if self.accessible(top):
                yield top
            else:
                raise RpcFileNotFoundError(f'cannot access: {top}')

        for root, dirs, files in self.walk(top, topdown=topdown):
            for name in files:
                yield os.path.join(root, name)
            for name in dirs:
                yield os.path.join(root, name)

        if not topdown:
            if self.accessible(top):
                yield top
            else:
                raise RpcFileNotFoundError(f'cannot access: {top}')

    @path_to_str('top')
    def walk(self, top: str, topdown=True, onerror=None):
        """ provides the same results as os.walk(top) """
        dirs = []
        files = []
        try:
            for entry in self.scandir(top):
                try:
                    if entry.is_dir():
                        dirs.append(entry.name)
                    else:
                        files.append(entry.name)
                except Exception as e:
                    if not onerror:
                        raise e
                    onerror(e)
        except Exception as e:
            if not onerror:
                raise e
            onerror(e)

        if topdown:
            yield top, dirs, files

        if dirs:
            for d in dirs:
                yield from self.walk(posixpath.join(top, d), topdown=topdown, onerror=onerror)

        if not topdown:
            yield top, dirs, files

    @contextlib.contextmanager
    @path_to_str('remote')
    def remote_file(self, remote: str):
        with tempfile.TemporaryDirectory() as local_dir:
            local = Path(local_dir) / Path(remote).parts[-1]
            if self.accessible(remote):
                self.pull(remote, local.absolute())
            try:
                yield local.absolute()
            finally:
                self.push(local, remote, force=True)

    @path_to_str('directory')
    def remote_temp_dir(self, directory: str = '/tmp', mode: int = 0o700) -> RemoteTemporaryDir:
        """Generate a random temp directory name and create it in the given directory (default '/tmp').

        :param directory: Directory to create the temp directory inside (default '/tmp').
        :param mode: Mode to create the temp directory with (default 0o700).
        """
        return RemoteTemporaryDir(self._client, directory, mode)
