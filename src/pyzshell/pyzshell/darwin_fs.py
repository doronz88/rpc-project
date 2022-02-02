import posixpath

from pyzshell.exceptions import BadReturnValueError
from pyzshell.fs import Fs
from pyzshell.structs.consts import S_IFDIR
from pyzshell.structs.darwin import dirent32, dirent64, stat32, stat64


class DarwinFs(Fs):
    CHUNK_SIZE = 1024

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

    def listdir(self, dirname: str) -> list:
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

    def walk(self, dirname: str):
        dirs = []
        files = []
        for file in self.listdir(dirname):
            filename = file.d_name
            if filename in ('.', '..', ''):
                continue
            infos = self.stat(posixpath.join(dirname, filename))
            if infos.st_mode & S_IFDIR:
                dirs.append(filename)
            else:
                files.append(filename)

        yield dirname, dirs, files

        if dirs:
            for d in dirs:
                for walk_result in self.walk(posixpath.join(dirname, d)):
                    yield walk_result
