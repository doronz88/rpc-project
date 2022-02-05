from pyzshell.client.client import Client
from pyzshell.darwin_processes import DarwinProcesses
from pyzshell.linux_fs import LinuxFs
from pyzshell.preferences import Preferences


class LinuxClient(Client):
    def __init__(self, sock, uname_version: str, hostname: str, port: int = None):
        super().__init__(sock, uname_version, hostname, port)
        self.fs = LinuxFs(self)
        self.prefs = Preferences(self)
        self.processes = DarwinProcesses(self)
