from pyzshell.exceptions import ZShellError, BadReturnValueError
from pyzshell.structs.consts import O_RDONLY, O_WRONLY, O_CREAT, O_TRUNC
from pyzshell.structs.generic import dirent32, dirent64, stat32, stat64


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

    def stat(self, filename: str):
        """ stat() filename at remote. read man for more details. """
        stat = stat32
        if self._client.inode64:
            stat = stat64
        with self._client.safe_malloc(stat.sizeof()) as buf:
            err = self._client.symbols.stat(filename, buf)
            if err != 0:
                raise BadReturnValueError(f'failed to stat(): {filename}')
            return stat.parse(buf.peek(stat.sizeof()))

    def dirlist(self, dirname: str) -> list:
        dirent = dirent32
        if self._client.inode64:
            dirent = dirent64

        result = []
        dp = self._client.symbols.opendir(dirname)
        if 0 == dp:
            raise BadReturnValueError(f'failed to opendir(): {dirname}')
        while True:
            ep = self._client.symbols.readdir(dp)
            if ep == 0:
                break
            entry = dirent.parse_stream(ep)
            result.append(entry)
        self._client.symbols.closedir(dp)
        return result

    def write_file(self, filename: str, buf: bytes, mode: int = 0o777) -> None:
        """ write file at target """
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
        """ read file at target """
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
