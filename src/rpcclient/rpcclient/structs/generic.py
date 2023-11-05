from construct import Bytes, CString, Default, FlagsEnum, FormatField, If, Int8ul, Int16sl, Int16ub, Int16ul, Int32ub, \
    Int32ul, Int64sl, Int64ul, LazyBound, PaddedString, Padding, Pointer, Struct, this

from rpcclient.structs.consts import AF_INET, AF_INET6, AF_UNIX

UNIX_PATH_MAX = 104

u_char = Int8ul
uint8_t = Int8ul
short = Int16sl
u_short = Int16ul
uint32_t = Int32ul
uint64_t = Int64ul
u_int32_t = uint32_t
uid_t = Int32ul
gid_t = Int32ul
time_t = Int32ul
long = Int64sl
mode_t = Int16ul
in_addr = Bytes(4)
in6_addr = Bytes(16)

sockaddr_in = Struct(
    'sin_family' / Default(Int16sl, AF_INET),
    'sin_port' / Int16ub,
    'sin_addr' / in_addr,
    'sin_zero' / Default(Bytes(8), b'\x00' * 8),
)

sockaddr_in6 = Struct(
    'sin6_family' / Default(Int16sl, AF_INET6),
    'sin6_port' / Int16ub,
    'sin6_flowinfo' / Default(Int32ub, 0),
    'sin6_addr' / in6_addr,
    'sin6_scope_id' / Default(Int32ub, 0),
)

sockaddr_un = Struct(
    'sun_len' / Default(Int8ul, 0),
    'sun_family' / Default(Int8ul, AF_UNIX),
    'sun_path' / PaddedString(UNIX_PATH_MAX, 'utf8'),
)

sockaddr = Struct(
    Padding(1),
    'sa_family' / Int8ul,
)

st_flags = FlagsEnum(Int32ul,
                     UF_NODUMP=1,
                     UF_IMMUTABLE=2,
                     UF_APPEND=4,
                     SF_ARCHIVED=0x00010000,
                     SF_IMMUTABLE=0x00020000,
                     SF_APPEND=0x00040000)


class SymbolFormatField(FormatField):
    """
    A Symbol wrapper for construct
    """

    def __init__(self, client):
        super().__init__('<', 'Q')
        self._client = client

    def _parse(self, stream, context, path):
        return self._client.symbol(FormatField._parse(self, stream, context, path))


def hostent(client) -> Struct:
    return Struct(
        '_h_name' / SymbolFormatField(client),
        'h_name' / Pointer(this._h_name, CString('utf8')),
        'h_aliases' / SymbolFormatField(client),
        'h_addrtype' / Int32ul,
        'h_length' / Int32ul,
        'h_addr_list' / SymbolFormatField(client),
    )


def ifaddrs(client) -> Struct:
    return Struct(
        '_ifa_next' / SymbolFormatField(client),
        'ifa_next' / If(this._ifa_next != 0, LazyBound(lambda: Pointer(this._ifa_next, ifaddrs(client)))),

        '_ifa_name' / SymbolFormatField(client),
        'ifa_name' / If(this._ifa_name != 0, Pointer(this._ifa_name, CString('utf8'))),

        'ifa_flags' / Int32ul,
        Padding(4),
        'ifa_addr' / SymbolFormatField(client),
        'ifa_netmask' / SymbolFormatField(client),
        'ifa_dstaddr' / SymbolFormatField(client),
        'ifa_data' / SymbolFormatField(client),
    )


def Dl_info(client) -> Struct:
    return Struct(
        '_dli_fname' / SymbolFormatField(client),
        'dli_fname' / Pointer(this._dli_fname, CString('utf8')),

        'dli_fbase' / SymbolFormatField(client),

        '_dli_sname' / SymbolFormatField(client),
        'dli_sname' / Pointer(this._dli_sname, CString('utf8')),

        'dli_saddr' / SymbolFormatField(client),
    )
