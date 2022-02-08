from construct import Int32ul, Int16ul, Struct, Int16sl, Bytes, Default, Int64sl, Const, PaddedString, Pointer, \
    this, CString, LazyBound, Padding, If, Int8ul, Int64ul

from rpcclient.structs.consts import AF_UNIX, AF_INET, AF_INET6
from rpcclient.symbol import SymbolFormatField

UNIX_PATH_MAX = 108

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
in6_addr = Bytes(8)

sockaddr_in = Struct(
    'sin_family' / Default(Int16sl, AF_INET),
    'sin_port' / Int16ul,
    'sin_addr' / in_addr,
    'sin_zero' / Default(Bytes(8), b'\x00' * 8),
)

sockaddr_in6 = Struct(
    'sin6_family' / Default(Int16sl, AF_INET6),
    'sin6_port' / Int16ul,
    'sin6_flowinfo' / Int32ul,
    'sin6_addr' / in6_addr,
    'sin6_scope_id' / Int32ul,
)

sockaddr_un = Struct(
    'sun_family' / Const(AF_UNIX, Int16sl),
    'sun_path' / PaddedString(UNIX_PATH_MAX, 'utf8'),
)

sockaddr = Struct(
    Padding(1),
    'sa_family' / Int8ul,
)


def hostent(client):
    return Struct(
        '_h_name' / SymbolFormatField(client),
        'h_name' / Pointer(this._h_name, CString('utf8')),
        'h_aliases' / SymbolFormatField(client),
        'h_addrtype' / Int32ul,
        'h_length' / Int32ul,
        'h_addr_list' / SymbolFormatField(client),
    )


def ifaddrs(client):
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
