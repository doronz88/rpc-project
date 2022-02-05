from struct import Struct
from typing import List

from pyzshell.fs import Fs

from pyzshell.exceptions import ZShellError
from pyzshell.structs.linux import dirent


class LinuxFs(Fs):
    CHUNK_SIZE = 1024

    def listdir(self, dirname='.') -> List[Struct]:
        """ list directory contents(at remote).
            calls readdir in a loop """
        errno = self._client.symbols.errno
        errno[0] = 0
        dir_list = []
        folder = self._client.symbols.opendir(dirname)
        if folder == 0:
            raise ZShellError('cannot open folder to listdir')
        diren = self._client.symbols.readdir(folder)
        while diren != 0:
            entry = dirent.parse_stream(diren)
            dir_list.append(entry)
            diren = self._client.symbols.readdir(folder)
        if errno[0] != 0:
            raise ZShellError(f'readdir for listdir failed. ({self._client.errno})')
        self._client.symbols.closedir(folder)
        return dir_list
