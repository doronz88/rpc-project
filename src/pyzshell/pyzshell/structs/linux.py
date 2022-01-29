from construct import Struct, PaddedString

_UTSNAME_LENGTH = 65

utsname = Struct(
    'sysname' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
    'nodename' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
    'release' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
    'version' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
    'machine' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
)
