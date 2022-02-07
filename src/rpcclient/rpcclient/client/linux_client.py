from cached_property import cached_property

from rpcclient.client.client import Client
from rpcclient.linux_fs import LinuxFs
from rpcclient.structs.linux import utsname


class LinuxClient(Client):
    def __init__(self, sock, uname_version: str, hostname: str, port: int = None):
        super().__init__(sock, uname_version, hostname, port)
        self.fs = LinuxFs(self)

    @cached_property
    def uname(self):
        with self.safe_calloc(utsname.sizeof()) as uname:
            assert 0 == self.symbols.uname(uname)
            return utsname.parse_stream(uname)
