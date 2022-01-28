from construct import Struct, PaddedString

_UTSNAME_LENGTH = 65

utsname_linux = Struct(
    'sysname' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
    'nodename' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
    'release' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
    'version' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
    'machine' / PaddedString(_UTSNAME_LENGTH, 'utf8'),
)

_SYS_NAMELEN = 256

utsname_darwin = Struct(
    'sysname' / PaddedString(_SYS_NAMELEN, 'utf8'),
    'nodename' / PaddedString(_SYS_NAMELEN, 'utf8'),
    'release' / PaddedString(_SYS_NAMELEN, 'utf8'),
    'version' / PaddedString(_SYS_NAMELEN, 'utf8'),
    'machine' / PaddedString(_SYS_NAMELEN, 'utf8'),
)