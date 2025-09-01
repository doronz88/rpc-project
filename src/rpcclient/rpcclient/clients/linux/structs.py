from construct import Bytes, Computed, Int8ul, Int16ul, Int32ul, Int64ul, PaddedString, Padding, Struct

_UTSNAME_LENGTH = 65
_D_NAME_LENGTH = 256

utsname = Struct(
    'sysname' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
    'nodename' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
    'release' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
    'version' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
    'machine' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
    'domainname' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
)

dirent = Struct(
    'd_ino' / Int32ul,
    Padding(4),
    'd_off' / Int64ul,
    'd_reclen' / Int16ul,
    'd_type' / Int8ul,
    '_d_name_bytes' / Bytes(_D_NAME_LENGTH),
    'd_name' / Computed(lambda x: x._d_name_bytes.split(b'\x00', 1)[0].decode())
)
