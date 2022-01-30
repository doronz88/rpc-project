from cached_property import cached_property

from pyzshell.client.client import Client
from pyzshell.structs.darwin import utsname
from pyzshell.symbol import DarwinSymbol


class DarwinClient(Client):

    def __init__(self, sock, uname_version: str, hostname: str, port: int = None):
        super().__init__(sock, uname_version, hostname, port)

    @property
    def modules(self):
        m = []
        for i in range(self.symbols._dyld_image_count()):
            m.append(self.symbols._dyld_get_image_name(i).peek_str())
        return m

    def symbol(self, symbol: int):
        """ at a symbol object from a given address """
        return DarwinSymbol.create(symbol, self)

    @cached_property
    def uname(self):
        with self.safe_malloc(utsname.sizeof()) as uname:
            assert 0 == self.symbols.uname(uname)
            return utsname.parse(uname.peek(utsname.sizeof()))
