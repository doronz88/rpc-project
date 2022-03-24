from cached_property import cached_property

from rpcclient.client import Client
from rpcclient.linux.fs import LinuxFs
from rpcclient.linux.structs import utsname
from rpcclient.protocol import arch_t


class LinuxClient(Client):
    def __init__(self, sock, sysname: str, arch: arch_t, hostname: str, port: int = None):
        super().__init__(sock, sysname, arch, hostname, port)
        self.fs = LinuxFs(self)

    @cached_property
    def uname(self):
        with self.safe_calloc(utsname.sizeof()) as uname:
            assert 0 == self.symbols.uname(uname)
            return utsname.parse_stream(uname)
