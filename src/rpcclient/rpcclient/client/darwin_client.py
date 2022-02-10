import struct
import typing

from cached_property import cached_property

from rpcclient.client.client import Client
from rpcclient.darwin.darwin_fs import DarwinFs
from rpcclient.darwin.darwin_media import DarwinMedia
from rpcclient.darwin.darwin_network import DarwinNetwork
from rpcclient.darwin.darwin_processes import DarwinProcesses
from rpcclient.darwin.preferences import Preferences
from rpcclient.exceptions import RpcClientException
from rpcclient.structs.darwin import utsname
from rpcclient.structs.darwin_consts import kCFNumberSInt64Type, kCFNumberDoubleType
from rpcclient.symbol import DarwinSymbol


class DarwinClient(Client):

    def __init__(self, sock, sysname: str, hostname: str, port: int = None):
        super().__init__(sock, sysname, hostname, port)
        self._dlsym_global_handle = -2  # RTLD_GLOBAL

        if 0 == self.dlopen("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation", 2):
            raise RpcClientException('failed to load CoreFoundation')

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
        self.media = DarwinMedia(self)
        self.network = DarwinNetwork(self)

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

    def cf(self, o: object):
        if isinstance(o, DarwinSymbol):
            # assuming it's already a cfobject
            return o
        elif isinstance(o, str):
            return self.symbols.CFStringCreateWithCString(0, o, 0)
        elif isinstance(o, bytes):
            return self.symbols.CFDataCreate(0, o, len(o))
        elif isinstance(o, bool):
            if o:
                return self.symbols.kCFBooleanTrue[0]
            else:
                return self.symbols.kCFBooleanFalse[0]
        elif isinstance(o, int):
            with self.safe_malloc(8) as buf:
                buf[0] = o
                return self.symbols.CFNumberCreate(0, kCFNumberSInt64Type, buf)
        elif isinstance(o, float):
            with self.safe_malloc(8) as buf:
                buf.poke(struct.pack('<d', o))
                return self.symbols.CFNumberCreate(0, kCFNumberDoubleType, buf)
        elif isinstance(o, list) or isinstance(o, tuple):
            cfvalues = [self.cf(i) for i in o]
            with self.safe_malloc(8 * len(cfvalues)) as buf:
                for i in range(len(cfvalues)):
                    buf[i] = cfvalues[i]
                return self.symbols.CFArrayCreate(0, buf, len(cfvalues), 0)
        elif isinstance(o, dict):
            cfkeys = [self.cf(i) for i in o.keys()]
            cfvalues = [self.cf(i) for i in o.values()]
            with self.safe_malloc(8 * len(cfkeys)) as keys_buf:
                with self.safe_malloc(8 * len(cfvalues)) as values_buf:
                    for i in range(len(cfkeys)):
                        keys_buf[i] = cfkeys[i]
                    for i in range(len(cfvalues)):
                        values_buf[i] = cfvalues[i]
                    return self.symbols.CFDictionaryCreate(0, keys_buf, values_buf, len(cfvalues), 0, 0, 0)
        else:
            raise NotImplementedError()
