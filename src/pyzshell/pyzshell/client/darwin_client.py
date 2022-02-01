import typing

from cached_property import cached_property

from pyzshell.DarwinFs import DarwinFs
from pyzshell.client.client import Client
from pyzshell.structs.darwin import utsname
from pyzshell.symbol import DarwinSymbol


class DarwinClient(Client):

    def __init__(self, sock, uname_version: str, hostname: str, port: int = None):
        super().__init__(sock, uname_version, hostname, port)
        if self.is_idevice:
            self.inode64 = True
        self.fs = DarwinFs(self)

    @property
    def modules(self) -> typing.List[str]:
        m = []
        for i in range(self.symbols._dyld_image_count()):
            m.append(self.symbols._dyld_get_image_name(i).peek_str())
        return m

    def symbol(self, symbol: int):
        """ at a symbol object from a given address """
        return DarwinSymbol.create(symbol, self)

    @cached_property
    def uname(self):
        with self.safe_calloc(utsname.sizeof()) as uname:
            uname.poke(b'\x00' * utsname.sizeof())
            assert 0 == self.symbols.uname(uname)
            return utsname.parse_stream(uname)

    @cached_property
    def is_idevice(self):
        return self.uname.machine.startswith('i')
