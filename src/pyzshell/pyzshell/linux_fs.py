from pyzshell.fs import Fs


class LinuxFs(Fs):
    CHUNK_SIZE = 1024

    def listdir(self, dirname: str) -> list:
        """ get directory listing for a given dirname """
        raise NotImplementedError()
