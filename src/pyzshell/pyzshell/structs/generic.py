from construct import Struct, PaddedString, Int8ul, Int16ul, Int32ul, this

dirent = Struct(
    'd_ino' / Int32ul,
    'd_offset' / Int16ul,
    'd_reclen' / Int8ul,
    'd_namelen' / Int8ul,
    'd_name' / PaddedString(this.d_namelen, 'utf8'),
)
