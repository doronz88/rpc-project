from construct import PaddedString, Struct

_SYS_NAMELEN = 256

utsname = Struct(
    'sysname' / PaddedString(_SYS_NAMELEN, 'utf8'),
    'nodename' / PaddedString(_SYS_NAMELEN, 'utf8'),
    'release' / PaddedString(_SYS_NAMELEN, 'utf8'),
    'version' / PaddedString(_SYS_NAMELEN, 'utf8'),
    'machine' / PaddedString(_SYS_NAMELEN, 'utf8'),
)
