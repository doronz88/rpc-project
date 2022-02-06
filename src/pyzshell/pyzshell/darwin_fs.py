from pyzshell.exceptions import BadReturnValueError, ZShellError
from pyzshell.fs import Fs
from pyzshell.structs.darwin import dirent32, dirent64, stat32, stat64, statfs64, statfs32


class DarwinFs(Fs):
    CHUNK_SIZE = 1024

    def stat(self, filename: str):
        """ stat(filename) at remote. read man for more details. """
        stat = stat32
        if self._client.inode64:
            stat = stat64
        with self._client.safe_malloc(stat.sizeof()) as buf:
            err = self._client.symbols.stat(filename, buf)
            if err != 0:
                raise BadReturnValueError(f'failed to stat(): {filename}')
            return stat.parse(buf.peek(stat.sizeof()))

    def listdir(self, dirname: str) -> list:
        """ get directory listing for a given dirname """
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

    def statfs(self, path: str):
        statfs = statfs64
        if self._client.inode64:
            statfs = statfs32
        with self._client.safe_malloc(statfs.sizeof()) as buf:
            if 0 != self._client.symbols.statfs(path, buf):
                raise ZShellError(f'statfs failed for: {path}')
            return statfs.parse_stream(buf)
