from cached_property import cached_property

from rpcclient.clients.linux.structs import utsname
from rpcclient.core.client import CoreClient


class LinuxClient(CoreClient):
    def __init__(self, sock, sysname: str, arch):
        super().__init__(sock, sysname, arch)

    @cached_property
    def uname(self):
        with self.safe_calloc(utsname.sizeof()) as uname:
            assert 0 == self.symbols.uname(uname)
            return utsname.parse_stream(uname)
