from pyzshell.exceptions import ZShellError
from pyzshell.structs.consts import O_RDONLY, O_WRONLY, O_CREAT, O_TRUNC


class Fs:
    CHUNK_SIZE = 1024

    def __init__(self, client):
        self._client = client

    def chmod(self, filename: str, mode: int):
        """ chmod() filename at remote. read man for more details. """
        return self._client.symbols.chmod(filename, mode)

    def remove(self, filename: str):
        """ remove() filename at remote. read man for more details. """
        return self._client.symbols.remove(filename)

    def mkdir(self, filename: str, mode: int):
        """ mkdir() filename at remote. read man for more details. """
        return self._client.symbols.mkdir(filename, mode)

    def write_file(self, filename: str, buf: bytes, mode: int = 0o777) -> None:
        """ write file at remote """
        fd = self._client.symbols.open(filename, O_WRONLY | O_CREAT | O_TRUNC, mode)
        if fd == 0xffffffff:
            raise ZShellError(f'failed to open: {filename} for writing')

        while buf:
            err = self._client.symbols.write(fd, buf, len(buf))
            if err == 0xffffffffffffffff:
                raise ZShellError(f'write failed for: {filename}')
            buf = buf[err:]

        self._client.symbols.close(fd)

    def read_file(self, filename: str) -> bytes:
        """ read file at remote """
        fd = self._client.symbols.open(filename, O_RDONLY)
        if fd == 0xffffffff:
            raise ZShellError(f'failed to open: {filename} for reading')

        buf = b''
        with self._client.safe_malloc(self.CHUNK_SIZE) as chunk:
            while True:
                err = self._client.symbols.read(fd, chunk, self.CHUNK_SIZE)
                if err == 0:
                    break
                elif err < 0:
                    raise ZShellError(f'read failed for: {filename}')
                buf += chunk.peek(err)
        self._client.symbols.close(fd)
        return buf

    def symlink(self, target: str, linkpath: str) -> int:
        """ symlink(target, linkpath) at remote. read man for more details. """
        err = self._client.symbols.symlink(target, linkpath)
        if err < 0:
            raise ZShellError(f'symlink failed for {target} and {linkpath}')
        return err
