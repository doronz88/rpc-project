from typing import List, Mapping

from parameter_decorators import path_to_str

from rpcclient.darwin.structs import stat64, statfs64
from rpcclient.fs import Fs


def do_stat(client, stat_name, filename: str):
    """ stat(filename) at remote. read man for more details. """
    with client.safe_malloc(stat64.sizeof()) as buf:
        err = client.symbols[stat_name](filename, buf)
        if err != 0:
            client.raise_errno_exception(f'failed to stat(): {filename}')
        return stat64.parse_stream(buf)


class DarwinFs(Fs):
    @path_to_str('path')
    def stat(self, path: str):
        """ stat(filename) at remote. read man for more details. """
        return do_stat(self._client, 'stat64', path)

    @path_to_str('path')
    def lstat(self, path: str):
        """ lstat(filename) at remote. read man for more details. """
        return do_stat(self._client, 'lstat64', path)

    @path_to_str('path')
    def setxattr(self, path: str, name: str, value: bytes):
        """ set an extended attribute value """
        count = self._client.symbols.setxattr(path, name, value, len(value), 0, 0).c_int64
        if count == -1:
            self._client.raise_errno_exception(f'failed to setxattr(): {path}')

    @path_to_str('path')
    def removexattr(self, path: str, name: str):
        """ remove an extended attribute value """
        count = self._client.symbols.removexattr(path, name, 0).c_int64
        if count == -1:
            self._client.raise_errno_exception(f'failed to removexattr(): {path}')

    @path_to_str('path')
    def listxattr(self, path: str) -> List[str]:
        """ list extended attribute names """
        max_buf_len = 1024
        with self._client.safe_malloc(max_buf_len) as xattributes_names:
            count = self._client.symbols.listxattr(path, xattributes_names, max_buf_len, 0).c_int64
            if count == -1:
                self._client.raise_errno_exception(f'failed to listxattr(): {path}')
            return [s.decode() for s in xattributes_names.peek(count).split(b'\x00')[:-1]]

    @path_to_str('path')
    def getxattr(self, path: str, name: str) -> bytes:
        """ get an extended attribute value """
        max_buf_len = 1024
        with self._client.safe_malloc(max_buf_len) as value:
            count = self._client.symbols.getxattr(path, name, value, max_buf_len, 0, 0).c_int64
            if count == -1:
                self._client.raise_errno_exception(f'failed to getxattr(): {path}')
            return value.peek(count)

    @path_to_str('path')
    def dictxattr(self, path: str) -> Mapping[str, bytes]:
        """ get a dictionary of all extended attributes """
        result = {}
        for k in self.listxattr(path):
            result[k] = self.getxattr(path, k)
        return result

    @path_to_str('path')
    def statfs(self, path: str):
        with self._client.safe_malloc(statfs64.sizeof()) as buf:
            if 0 != self._client.symbols.statfs64(path, buf):
                self._client.raise_errno_exception(f'statfs failed for: {path}')
            return statfs64.parse_stream(buf)

    @path_to_str('path')
    def chflags(self, path: str, flags: int) -> None:
        """ call chflags(path, flags) at remote. see manpage for more info """
        if 0 != self._client.symbols.chflags(path, flags):
            self._client.raise_errno_exception(f'chflags failed for: {path}')
