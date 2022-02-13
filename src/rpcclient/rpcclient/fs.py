import posixpath
from typing import Iterator, List

from rpcclient.common import path_to_str
from rpcclient.exceptions import InvalidArgumentError, BadReturnValueError
from rpcclient.structs.consts import O_RDONLY, O_WRONLY, O_CREAT, O_TRUNC, S_IFMT, S_IFDIR, O_RDWR, SEEK_CUR, S_IFREG, \
    DT_LNK, DT_UNKNOWN, S_IFLNK, DT_REG, DT_DIR


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
        if self._entry.get('d_type', DT_UNKNOWN) != DT_UNKNOWN:
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
        need_stat = True
        if 'd_type' in self._entry:
            is_symlink = self._entry.d_type == DT_LNK
            need_stat = self._entry.d_type == DT_UNKNOWN or (follow_symlinks and is_symlink)
        if not need_stat:
            d_types = {S_IFLNK: DT_LNK, S_IFDIR: DT_DIR, S_IFREG: DT_REG}
            return self._entry.d_type == d_types[mode]
        else:
            st_mode = self.stat(follow_symlinks=follow_symlinks).st_mode
            if not st_mode:
                raise BadReturnValueError(f'failed to stat(): {self.path}')
            return (st_mode & S_IFMT) == mode

    def _get_lstat(self):
        if self._lstat is None:
            self._lstat = self._fetch_stat(False)
        return self._lstat

    def _fetch_stat(self, follow_symlinks):
        raise NotImplementedError()


class ScandirIterator:
    def __init__(self, path, dirp, client):
        self.path = path
        self._client = client
        self._dirp = dirp

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:  # noqa: E722
            # Best effort.
            pass

    def __iter__(self) -> Iterator[DirEntry]:
        raise NotImplementedError()

    def is_closed(self):
        return not self._dirp

    def close(self):
        if self.is_closed():
            return
        self.closedir()
        self._dirp = 0

    def closedir(self):
        raise NotImplementedError()


class File:
    CHUNK_SIZE = 1024

    def __init__(self, client, fd: int):
        """
        :param rpcclient.client.client.Client client:
        :param fd:
        """
        self._client = client
        self.fd = fd

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """ close(fd) at remote. read man for more details. """
        fd = self._client.symbols.close(self.fd).c_int32
        if fd < 0:
            raise BadReturnValueError(f'failed to close fd: {fd}')

    def seek(self, offset: int, whence: int) -> int:
        """ lseek(fd, offset, whence) at remote. read man for more details. """
        err = self._client.symbols.lseek(self.fd, offset, whence).c_int32
        if err < 0:
            raise BadReturnValueError(f'failed to lseek fd: {self.fd}')
        return err

    def tell(self) -> int:
        return self.seek(0, SEEK_CUR)

    def write(self, buf: bytes) -> int:
        """ write(fd, buf, size) at remote. read man for more details. """
        n = self._client.symbols.write(self.fd, buf, len(buf)).c_int64
        if n < 0:
            raise BadReturnValueError(f'failed to write on fd: {self.fd}')
        return n

    def writeall(self, buf: bytes):
        """ continue call write() until """
        while buf:
            err = self.write(buf)
            buf = buf[err:]

    def read(self, size: int = CHUNK_SIZE) -> bytes:
        """ read file at remote """
        with self._client.safe_malloc(size) as chunk:
            err = self._client.symbols.read(self.fd, chunk, self.CHUNK_SIZE).c_int64
            if err < 0:
                raise BadReturnValueError(f'read failed for fd: {self.fd}')
            return chunk.peek(err)

    def readall(self, chunk_size: int = CHUNK_SIZE) -> bytes:
        """ read file at remote """
        buf = b''
        with self._client.safe_malloc(chunk_size) as chunk:
            while True:
                err = self._client.symbols.read(self.fd, chunk, chunk_size).c_int64
                if err == 0:
                    # EOF
                    break
                if err < 0:
                    raise BadReturnValueError(f'read failed for fd: {self.fd}')
                buf += chunk.peek(err)
        return buf


class Fs:
    def __init__(self, client):
        self._client = client

    @path_to_str('path')
    def chown(self, path: str, uid: int, gid: int):
        """ chmod(path, mode) at remote. read man for more details. """
        if self._client.symbols.chown(path, uid, gid).c_int32 < 0:
            raise BadReturnValueError(f'failed to chown: {path} ({self._client.last_error})')

    @path_to_str('path')
    def chmod(self, path: str, mode: int):
        """ chmod(path, mode) at remote. read man for more details. """
        if self._client.symbols.chmod(path, mode).c_int32 < 0:
            raise BadReturnValueError(f'failed to chmod: {path} ({self._client.last_error})')

    @path_to_str('path')
    def remove(self, path: str):
        """ remove(path) at remote. read man for more details. """
        if self._client.symbols.remove(path).c_int32 < 0:
            raise BadReturnValueError(f'failed to remove: {path} ({self._client.last_error})')

    @path_to_str('path')
    def mkdir(self, path: str, mode: int):
        """ mkdir(path, mode) at remote. read man for more details. """
        if self._client.symbols.mkdir(path, mode).c_int64 < 0:
            raise BadReturnValueError(f'failed to mkdir: {path} ({self._client.last_error})')

    @path_to_str('path')
    def chdir(self, path: str):
        """ chdir(path) at remote. read man for more details. """
        if self._client.symbols.chdir(path).c_int64 < 0:
            raise BadReturnValueError(f'failed to chdir: {path} ({self._client.last_error})')

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
            'w+' - read and write. create if doesn't exist.
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
            raise InvalidArgumentError(f'mode can be only one of: {available_modes.keys()}')

        fd = self._client.symbols.open(file, mode, access).c_int32
        if fd < 0:
            raise BadReturnValueError(f'failed to open: {file} ({self._client.last_error})')
        return File(self._client, fd)

    @path_to_str('src', 'dst')
    def symlink(self, src: str, dst: str) -> int:
        """ symlink(src, dst) at remote. read man for more details. """
        err = self._client.symbols.symlink(src, dst).c_int64
        if err < 0:
            raise BadReturnValueError(
                f'symlink failed to create link: {dst}->{src} ({self._client.last_error})')
        return err

    @path_to_str('src', 'dst')
    def link(self, src: str, dst: str) -> int:
        """ link(src, dst) - hardlink at remote. read man for more details. """
        err = self._client.symbols.link(src, dst).c_int64
        if err < 0:
            raise BadReturnValueError(f'link failed to create link: {dst}->{src} ({self._client.last_error})')
        return err

    def pwd(self) -> str:
        """ calls getcwd(buf, size_t) and prints current path.
            with the special values NULL, 0 the buffer is allocated dynamically """
        chunk = self._client.symbols.getcwd(0, 0)
        if chunk == 0:
            raise BadReturnValueError(f'pwd failed ({self._client.last_error})')
        buf = chunk.peek_str()
        self._client.symbols.free(chunk)
        return buf

    @path_to_str('path')
    def listdir(self, path: str = '.') -> List[str]:
        """ get directory listing for a given dirname """
        with self.scandir(path) as it:
            return [e.name for e in it]

    @path_to_str('path')
    def scandir(self, path: str = '.') -> ScandirIterator:
        """ get directory listing for a given dirname """
        raise NotImplementedError()

    @path_to_str('path')
    def stat(self, path: str):
        """ stat(filename) at remote. read man for more details. """
        raise NotImplementedError()

    @path_to_str('top')
    def walk(self, top: str):
        """ provides the same results as os.walk(top) """
        dirs = []
        files = []
        for entry in self.scandir(top):
            if entry.is_dir():
                dirs.append(entry.name)
            else:
                files.append(entry.name)

        yield top, dirs, files

        if dirs:
            for d in dirs:
                for walk_result in self.walk(posixpath.join(top, d)):
                    yield walk_result
