from pyzshell.client.client import Client
from pyzshell.linux_fs import LinuxFs


class LinuxClient(Client):
    def __init__(self, sock, uname_version: str, hostname: str, port: int = None):
        super().__init__(sock, uname_version, hostname, port)
        self.fs = LinuxFs(self)
