from construct import Int32ul, Int16ul, Struct, Int16sl, Bytes, Default, Int64sl, Const, PaddedString

from pyzshell.structs.consts import AF_UNIX, AF_INET

UNIX_PATH_MAX = 108

uid_t = Int32ul
gid_t = Int32ul
time_t = Int32ul
long = Int64sl
mode_t = Int16ul
in_addr = Bytes(4)

sockaddr_in = Struct(
    'sin_family' / Const(AF_INET, Int16sl),
    'sin_port' / Int16ul,
    'sin_addr' / in_addr,
    'sin_zero' / Default(Bytes(8), b'\x00' * 8),
)

sockaddr_un = Struct(
    'sun_family' / Const(AF_UNIX, Int16sl),
    'sun_path' / PaddedString(UNIX_PATH_MAX, 'utf8'),
)
