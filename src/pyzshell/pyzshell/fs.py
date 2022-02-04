from pyzshell.exceptions import ZShellError
from pyzshell.structs.consts import O_RDONLY, O_WRONLY, O_CREAT, O_TRUNC


class Fs:
    CHUNK_SIZE = 1024

    def __init__(self, client):
        self._client = client

    def chmod(self, filename: str, mode: int):
        """ chmod(filename, mode)at remote. read man for more details. """
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
        """ chdir(filename) filename at remote. read man for more details. """
        if self._client.symbols.chdir(filename).c_int64 < 0:
            raise ZShellError(f'failed to chdir: {filename}')

    def write_file(self, filename: str, buf: bytes, mode: int = 0o777) -> None:
        """ write file at remote """
        fd = self._client.symbols.open(filename, O_WRONLY | O_CREAT | O_TRUNC, mode).c_int32
        if fd < 0:
            raise ZShellError(f'failed to open: {filename} for writing')

        while buf:
            err = self._client.symbols.write(fd, buf, len(buf)).c_int64
            if err < 0:
                raise ZShellError(f'write failed for: {filename}')
            buf = buf[err:]

        self._client.symbols.close(fd)

    def read_file(self, filename: str) -> bytes:
        """ read file at remote """
        fd = self._client.symbols.open(filename, O_RDONLY).c_int32
        if fd < 0:
            raise ZShellError(f'failed to open: {filename} for reading')

        buf = b''
        with self._client.safe_malloc(self.CHUNK_SIZE) as chunk:
            while True:
                err = self._client.symbols.read(fd, chunk, self.CHUNK_SIZE).c_int64
                if err == 0:
                    break
                elif err < 0:
                    raise ZShellError(f'read failed for: {filename}')
                buf += chunk.peek(err)
        self._client.symbols.close(fd)
        return buf

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
