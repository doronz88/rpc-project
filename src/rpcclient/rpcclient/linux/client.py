from typing import Callable

from cached_property import cached_property

from rpcclient.client import Client
from rpcclient.linux.structs import utsname
from rpcclient.protocol import arch_t


class LinuxClient(Client):
    def __init__(self, sock, sysname: str, arch: arch_t, create_socket_cb: Callable):
        super().__init__(sock, sysname, arch, create_socket_cb)

    @cached_property
    def uname(self):
        with self.safe_calloc(utsname.sizeof()) as uname:
            assert 0 == self.symbols.uname(uname)
            return utsname.parse_stream(uname)
