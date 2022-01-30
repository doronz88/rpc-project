from construct import Struct, PaddedString, Int8ul, Int16ul, Int32ul, this, Int64ul

dirent32 = Struct(
    'd_ino' / Int32ul,
    'd_offset' / Int16ul,
    'd_reclen' / Int8ul,
    'd_namelen' / Int8ul,
    'd_name' / PaddedString(this.d_namelen, 'utf8'),
)

dirent64 = Struct(
    'd_ino' / Int64ul,
    'd_offset' / Int64ul,
    'd_reclen' / Int16ul,
    'd_namelen' / Int16ul,
    'd_type' / Int8ul,
    'd_name' / PaddedString(this.d_namelen, 'utf8'),
)
