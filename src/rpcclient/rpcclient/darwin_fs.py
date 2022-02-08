from pathlib import Path
from typing import Union

from rpcclient.exceptions import BadReturnValueError
from rpcclient.fs import Fs, DirEntry, ScandirIterator
from rpcclient.structs.darwin import dirent32, dirent64, stat64, statfs64


def do_stat(client, stat_name, filename):
    """ stat(filename) at remote. read man for more details. """
    with client.safe_malloc(stat64.sizeof()) as buf:
        err = client.symbols[stat_name](filename, buf)
        if err != 0:
            raise BadReturnValueError(f'failed to stat(): {filename}')
        return stat64.parse_stream(buf)


class DarwinDirEntry(DirEntry):
    def _fetch_stat(self, follow_symlinks):
        stat_name = 'stat64' if follow_symlinks else 'lstat64'
        return do_stat(self._client, stat_name, self.path)


class DarwinScandirIterator(ScandirIterator):
    def __enter__(self):
        return self

    def __iter__(self):
        dirent = dirent32
        if self._client.inode64:
            dirent = dirent64

        while True:
            self._client.errno = 0
            direntp = self._client.symbols.readdir(self._dirp)
            if not direntp:
                if self._client.errno:
                    raise BadReturnValueError(f'Failed scanning dir: {self._client.last_error}')
                break
            entry = dirent.parse_stream(direntp)
            if entry.d_name in ('.', '..'):
                continue
            yield DarwinDirEntry(self.path, entry, self._client)

    def close(self):
        self._client.symbols.closedir(self._dirp)


class DarwinFs(Fs):
    CHUNK_SIZE = 1024

    def stat(self, path: Union[str, Path]):
        """ stat(filename) at remote. read man for more details. """
        # In case path is instance of pathlib.Path
        path = str(path)
        return do_stat(self._client, 'stat64', path)

    def scandir(self, path: Union[str, Path] = '.'):
        # In case path is instance of pathlib.Path
        path = str(path)
        dp = self._client.symbols.opendir(path)
        if not dp:
            raise BadReturnValueError(f'failed to opendir(): {path} ({self._client.last_error})')
        return DarwinScandirIterator(path, dp, self._client)

    def statfs(self, path: str):
        with self._client.safe_malloc(statfs64.sizeof()) as buf:
            if 0 != self._client.symbols.statfs64(path, buf):
                raise BadReturnValueError(f'statfs failed for: {path}')
            return statfs64.parse_stream(buf)
