from pyzshell.client.client import Client
from pyzshell.linux_fs import LinuxFs


class LinuxClient(Client):
    def __init__(self, sock, sysname: str, hostname: str, port: int = None):
        super().__init__(sock, sysname, hostname, port)
        self.fs = LinuxFs(self)
