import typing

from cached_property import cached_property

from rpcclient.client.client import Client
from rpcclient.darwin_fs import DarwinFs
from rpcclient.darwin_processes import DarwinProcesses
from rpcclient.preferences import Preferences
from rpcclient.structs.darwin import utsname
from rpcclient.symbol import DarwinSymbol


class DarwinClient(Client):

    def __init__(self, sock, sysname: str, hostname: str, port: int = None):
        super().__init__(sock, sysname, hostname, port)
        self._dlsym_global_handle = -2  # RTLD_GLOBAL

        self.dlopen("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation", 2)
        self._cf_types = {
            self.symbols.CFDateGetTypeID(): 'date',
            self.symbols.CFDataGetTypeID(): 'data',
            self.symbols.CFStringGetTypeID(): 'str',
            self.symbols.CFArrayGetTypeID(): 'array',
            self.symbols.CFBooleanGetTypeID(): 'bool',
            self.symbols.CFNumberGetTypeID(): 'number',
            self.symbols.CFSetGetTypeID(): 'set',
            self.symbols.CFDictionaryGetTypeID(): 'dict',
        }

        if self.uname.machine != 'x86_64':
            self.inode64 = True
        self.fs = DarwinFs(self)
        self.prefs = Preferences(self)
        self.processes = DarwinProcesses(self)

    @property
    def modules(self) -> typing.List[str]:
        m = []
        for i in range(self.symbols._dyld_image_count()):
            m.append(self.symbols._dyld_get_image_name(i).peek_str())
        return m

    @cached_property
    def uname(self):
        with self.safe_calloc(utsname.sizeof()) as uname:
            assert 0 == self.symbols.uname(uname)
            return utsname.parse_stream(uname)

    @cached_property
    def is_idevice(self):
        return self.uname.machine.startswith('i')

    def symbol(self, symbol: int):
        """ at a symbol object from a given address """
        return DarwinSymbol.create(symbol, self)

    def cfstr(self, s: str) -> DarwinSymbol:
        return self.symbols.CFStringCreateWithCString(0, s, 0)
