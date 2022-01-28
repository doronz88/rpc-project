import os

from pyzshell.exceptions import ZShellError


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

    def write_file(self, filename: str, buf: bytes):
        """ write file at target """
        fd = self._client.symbols.open(filename, os.O_WRONLY | os.O_CREAT, 0o0777)
        if fd == 0xffffffff:
            raise ZShellError(f'failed to open: {filename} for writing')

        while buf:
            err = self._client.symbols.write(fd, buf, len(buf))
            if err == 0xffffffffffffffff:
                raise ZShellError(f'write failed for: {filename}')
            buf = buf[err:]

        self._client.symbols.close(fd)
        return buf

    def read_file(self, filename: str) -> bytes:
        """ read file at target """
        fd = self._client.symbols.open(filename, os.O_RDONLY)
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
