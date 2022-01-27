from construct import Struct, Int32ul, PrefixedArray, Const, Enum, this, PascalString, Switch, Bytes, Int32sl

cmd_type_t = Enum(Int32ul,
                  CMD_EXEC=0,
                  )
MAGIC = 0x12345678

cmd_exec_t = Struct(
    'argv' / PrefixedArray(Int32ul, PascalString(Int32ul, 'utf8')),
)

protocol_message_t = Struct(
    'magic' / Const(MAGIC, Int32ul),
    'cmd_type' / cmd_type_t,
    'data' / Switch(this.cmd_type, {
        cmd_type_t.CMD_EXEC: cmd_exec_t,
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
