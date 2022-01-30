from construct import Struct, Int32ul, PrefixedArray, Const, Enum, this, PascalString, Switch, Int32sl, \
    PaddedString, Bytes, Int64ul

cmd_type_t = Enum(Int32ul,
                  CMD_EXEC=0,
                  CMD_DLOPEN=1,
                  CMD_DLCLOSE=2,
                  CMD_DLSYM=3,
                  CMD_CALL=4,
                  CMD_PEEK=5,
                  CMD_POKE=6,
                  )
MAGIC = 0x12345678
MAX_PATH_LEN = 1024
UNAME_VERSION_LEN = 256

cmd_exec_t = Struct(
    'argv' / PrefixedArray(Int32ul, PascalString(Int32ul, 'utf8')),
    'envp' / PrefixedArray(Int32ul, PascalString(Int32ul, 'utf8')),
)

cmd_dlopen_t = Struct(
    'filename' / PaddedString(MAX_PATH_LEN, 'utf8'),
    'mode' / Int32ul,
)

cmd_dlclose_t = Struct(
    'lib' / Int64ul,
)

cmd_dlsym_t = Struct(
    'lib' / Int64ul,
    'symbol_name' / PaddedString(MAX_PATH_LEN, 'utf8'),
)

cmd_call_t = Struct(
    'address' / Int64ul,
    'argv' / PrefixedArray(Int64ul, Int64ul),
)

cmd_peek_t = Struct(
    'address' / Int64ul,
    'size' / Int64ul,
)

cmd_poke_t = Struct(
    'address' / Int64ul,
    'size' / Int64ul,
    'data' / Bytes(this.size),
)

protocol_message_t = Struct(
    'magic' / Const(MAGIC, Int32ul),
    'cmd_type' / cmd_type_t,
    'data' / Switch(this.cmd_type, {
        cmd_type_t.CMD_EXEC: cmd_exec_t,
        cmd_type_t.CMD_DLOPEN: cmd_dlopen_t,
        cmd_type_t.CMD_DLCLOSE: cmd_dlclose_t,
        cmd_type_t.CMD_DLSYM: cmd_dlsym_t,
        cmd_type_t.CMD_CALL: cmd_call_t,
        cmd_type_t.CMD_PEEK: cmd_peek_t,
        cmd_type_t.CMD_POKE: cmd_poke_t,
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
