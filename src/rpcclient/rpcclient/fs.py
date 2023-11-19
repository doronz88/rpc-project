import contextlib
import os
import posixpath
import tempfile
from pathlib import Path
from typing import List

from parameter_decorators import path_to_str

from rpcclient.allocated import Allocated
from rpcclient.darwin.structs import MAXPATHLEN
from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.exceptions import ArgumentError, BadReturnValueError, RpcClientException, RpcFileExistsError, \
    RpcFileNotFoundError, RpcIsADirectoryError
from rpcclient.structs.consts import DT_DIR, DT_LNK, DT_REG, DT_UNKNOWN, O_CREAT, O_RDONLY, O_RDWR, O_TRUNC, O_WRONLY, \
    R_OK, S_IFDIR, S_IFLNK, S_IFMT, S_IFREG, SEEK_CUR


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
            self._client.raise_errno_exception(f'failed to stat: {self._entry.name}')
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

    def write(self, buf: bytes):
        """ continue call write() until """
        while buf:
            err = self._write(buf)
            buf = buf[err:]

    def _read(self, buf: DarwinSymbol, size: int) -> bytes:
        """ read file at remote """
        err = self._client.symbols.read(self.fd, buf, size).c_int64
        if err < 0:
            self._client.raise_errno_exception(f'read() failed for fd: {self.fd}')
        return buf.peek(err)

    def read(self, size: int = -1, chunk_size: int = CHUNK_SIZE) -> bytes:
        """ read file at remote """
        if size != -1 and size < chunk_size:
            chunk_size = size

        buf = b''
        with self._client.safe_malloc(chunk_size) as chunk:
            while size == -1 or len(buf) < size:
                read_chunk = self._read(chunk, chunk_size)
                if not read_chunk:
                    # EOF
                    break
                buf += read_chunk
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


class Fs:
    """ filesystem utils """

    def __init__(self, client):
        self._client = client

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
        mode = available_modes.get(mode)
        if mode is None:
            raise ArgumentError(f'mode can be only one of: {available_modes.keys()}')

        fd = self._client.symbols.open(file, mode, access).c_int32
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

    @path_to_str('remote')
    @path_to_str('local')
    def _pull_file(self, remote: str, local: str):
        with open(local, 'wb') as local_file:
            with self.open(remote, 'r') as remote_file:
                buf = remote_file.read(File.CHUNK_SIZE)
                while len(buf) > 0:
                    local_file.write(buf)
                    buf = remote_file.read(File.CHUNK_SIZE)

    @path_to_str('remote')
    @path_to_str('local')
    def _push_file(self, local: str, remote: str):
        with open(local, 'rb') as f:
            self.write_file(remote, f.read())

    @path_to_str('remote')
    @path_to_str('local')
    def pull(self, remote: str, local: str, onerror=None):
        """ pull complete directory tree """
        if self.is_file(remote):
            self._pull_file(remote, local)
            return

        cwd = os.getcwd()
        remote = Path(remote)
        local = Path(local)

        try:
            for root, dirs, files in self.walk(remote, topdown=True, onerror=onerror):
                local_root = local / Path(root).relative_to(remote)
                local_root.mkdir(exist_ok=True)
                os.chdir(str(local_root))
                for name in dirs:
                    Path(name).mkdir(exist_ok=True)
                for name in files:
                    try:
                        self._pull_file(os.path.join(root, name), name)
                    except RpcClientException as e:
                        if onerror:
                            onerror(e)
                        else:
                            raise
        finally:
            os.chdir(cwd)

    @path_to_str('local')
    @path_to_str('remote')
    def push(self, local: str, remote: str, onerror=None):
        """ push complete directory tree """
        cwd = self.pwd()
        remote = Path(remote)
        local = Path(local)

        if local.is_file():
            self._push_file(local, remote)
            return

        try:
            for root, dirs, files in os.walk(local, topdown=True, onerror=onerror):
                remote_root = remote / Path(root).relative_to(local)
                self.mkdir(remote_root, exist_ok=True)
                self.chdir(remote_root)
                for name in dirs:
                    self.mkdir(name, exist_ok=True)
                for name in files:
                    try:
                        self._push_file(os.path.join(root, name), name)
                    except RpcClientException as e:
                        if onerror:
                            onerror(e)
                        else:
                            raise
        finally:
            self.chdir(cwd)

    @path_to_str('file')
    def touch(self, file: str, mode: int = None):
        """ simulate unix touch command for given file """
        with self.open(file, 'w+'):
            pass
        if mode is not None:
            self.chmod(file, mode)

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
    def listdir(self, path: str = '.') -> List[str]:
        """ get directory listing for a given dirname """
        return [e.name for e in self.scandir(path)]

    @path_to_str('path')
    def scandir(self, path: str = '.') -> List[DirEntry]:
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
                for walk_result in self.walk(posixpath.join(top, d), topdown=topdown, onerror=onerror):
                    yield walk_result

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
                pass
