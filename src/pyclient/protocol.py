from construct import Struct, Int32ul, PrefixedArray, Const, Enum, this, PascalString, Switch, Int32sl, \
    PaddedString, Bytes, Int64ul, Int64sl

cmd_type_t = Enum(Int32ul,
                  CMD_EXEC=0,
                  CMD_OPEN=1,
                  CMD_CLOSE=2,
                  CMD_WRITE=3,
                  CMD_READ=4,
                  CMD_REMOVE=5,
                  CMD_MKDIR=6,
                  CMD_CHMOD=7,
                  )
MAGIC = 0x12345678
MAX_PATH_LEN = 1024
fd_t = Int64sl

cmd_exec_t = Struct(
    'argv' / PrefixedArray(Int32ul, PascalString(Int32ul, 'utf8')),
)

cmd_open_t = Struct(
    'filename' / PaddedString(MAX_PATH_LEN, 'utf8'),
    'mode' / Int32ul,
)

cmd_mkdir_t = Struct(
    'filename' / PaddedString(MAX_PATH_LEN, 'utf8'),
    'mode' / Int32ul,
)

cmd_remove_t = Struct(
    'filename' / PaddedString(MAX_PATH_LEN, 'utf8'),
)

cmd_chmod_t = Struct(
    'filename' / PaddedString(MAX_PATH_LEN, 'utf8'),
    'mode' / Int32ul,
)

cmd_read_t = Struct(
    'fd' / fd_t,
    'size' / Int64ul,
)

cmd_write_t = Struct(
    'fd' / fd_t,
    'size' / Int64ul,
    'data' / Bytes(this.size),
)

cmd_close_t = Struct(
    'fd' / Int64sl,
)

protocol_message_t = Struct(
    'magic' / Const(MAGIC, Int32ul),
    'cmd_type' / cmd_type_t,
    'data' / Switch(this.cmd_type, {
        cmd_type_t.CMD_EXEC: cmd_exec_t,
        cmd_type_t.CMD_OPEN: cmd_open_t,
        cmd_type_t.CMD_CLOSE: cmd_close_t,
        cmd_type_t.CMD_MKDIR: cmd_mkdir_t,
        cmd_type_t.CMD_REMOVE: cmd_remove_t,
        cmd_type_t.CMD_CHMOD: cmd_chmod_t,
        cmd_type_t.CMD_READ: cmd_read_t,
        cmd_type_t.CMD_WRITE: cmd_write_t,
    })
)

exec_chunk_type_t = Enum(Int32ul,
                         CMD_EXEC_CHUNK_TYPE_STDOUT=0,
                         CMD_EXEC_CHUNK_TYPE_ERRORCODE=1,
                         )

exec_chunk_t = Struct(
    'chunk_type' / exec_chunk_type_t,
    'size' / Int32ul,
)

pid_t = Int32ul
exitcode_t = Int32sl
