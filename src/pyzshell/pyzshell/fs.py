import posixpath

from pyzshell.exceptions import ZShellError, InvalidArgumentError
from pyzshell.structs.consts import O_RDONLY, O_WRONLY, O_CREAT, O_TRUNC, S_IFMT, S_IFDIR


class File:
    CHUNK_SIZE = 1024

    def __init__(self, client, fd: int):
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
            raise ZShellError(f'failed to close fd: {fd}')

    def write(self, buf: bytes, size: int) -> int:
        """ write(fd, buf, size) at remote. read man for more details. """
        n = self._client.symbols.write(self.fd, buf, size).c_int64
        if n < 0:
            raise ZShellError(f'failed to write on fd: {self.fd}')
        return n

    def writeall(self, buf: bytes):
        """ continue call write() until """
        while buf:
            err = self.write(buf, len(buf))
            buf = buf[err:]

    def read(self, size: int = CHUNK_SIZE) -> bytes:
        """ read file at remote """
        with self._client.safe_malloc(size) as chunk:
            err = self._client.symbols.read(self.fd, chunk, self.CHUNK_SIZE).c_int64
            if err < 0:
                raise ZShellError(f'read failed for fd: {self.fd}')
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
                    raise ZShellError(f'read failed for fd: {self.fd}')
                buf += chunk.peek(err)
        return buf


class Fs:
    def __init__(self, client):
        self._client = client

    def chmod(self, filename: str, mode: int):
        """ chmod(filename, mode) at remote. read man for more details. """
        if self._client.symbols.chmod(filename, mode).c_int32 < 0:
            raise ZShellError(f'failed to chmod: {filename}')

    def remove(self, filename: str):
        """ remove(filename) at remote. read man for more details. """
        if self._client.symbols.remove(filename).c_int32 < 0:
            raise ZShellError(f'failed to remove: {filename}')

    def mkdir(self, filename: str, mode: int):
        """ mkdir(filename, mode) at remote. read man for more details. """
        if self._client.symbols.mkdir(filename, mode).c_int64 < 0:
            raise ZShellError(f'failed to mkdir: {filename}')

    def chdir(self, filename: str):
        """ chdir(filename) at remote. read man for more details. """
        if self._client.symbols.chdir(filename).c_int64 < 0:
            raise ZShellError(f'failed to chdir: {filename}')

    def open(self, filename: str, mode: str, access: int = 0o777) -> File:
        """
        call open(filename, mode, access) at remote and get a context manager
        file object
        :param filename: filename to be opened
        :param mode: 'r' for read or 'w' for write
        :param access: access mode as octal value
        :return: a context manager file object
        """
        if mode == 'r':
            mode = O_RDONLY
        elif mode == 'w':
            mode = O_WRONLY | O_CREAT | O_TRUNC
        else:
            raise InvalidArgumentError(f'mode can be either "r" or "w". got: {mode}')

        fd = self._client.symbols.open(filename, mode, access).c_int32
        if fd < 0:
            raise ZShellError(f'failed to open: {filename} for writing')
        return File(self._client, fd)

    def symlink(self, target: str, linkpath: str) -> int:
        """ symlink(target, linkpath) at remote. read man for more details. """
        err = self._client.symbols.symlink(target, linkpath).c_int64
        if err < 0:
            raise ZShellError(f'symlink failed to create link: {linkpath}->{target}')
        return err

    def link(self, target: str, linkpath: str) -> int:
        """ link(target, linkpath) - hardlink at remote. read man for more details. """
        err = self._client.symbols.link(target, linkpath).c_int64
        if err < 0:
            raise ZShellError(f'link failed to create link: {linkpath}->{target}')
        return err

    def pwd(self) -> str:
        """ calls getcwd(buf, size_t) and prints current path.
            with the special values NULL, 0 the buffer is allocated dynamically """
        chunk = self._client.symbols.getcwd(0, 0)
        if chunk == 0:
            raise ZShellError('pwd failed.')
        buf = chunk.peek_str()
        self._client.symbols.free(chunk)
        return buf

    def listdir(self, dirname: str) -> list:
        """ get directory listing for a given dirname """
        raise NotImplementedError()

    def stat(self, filename: str):
        """ stat(filename) at remote. read man for more details. """
        raise NotImplementedError()

    def walk(self, dirname: str):
        """ provides the same results as os.walk(dirname) """
        dirs = []
        files = []
        for file in self.listdir(dirname):
            filename = file.d_name
            if filename in ('.', '..'):
                continue
            infos = self.stat(posixpath.join(dirname, filename))
            if infos.st_mode & S_IFMT == infos.st_mode & S_IFDIR:
                dirs.append(filename)
            else:
                files.append(filename)

        yield dirname, dirs, files

        if dirs:
            for d in dirs:
                for walk_result in self.walk(posixpath.join(dirname, d)):
                    yield walk_result
