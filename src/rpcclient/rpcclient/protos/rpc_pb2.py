# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: rpc.proto
# Protobuf Python Version: 4.25.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\trpc.proto\x12\x03rpc\"\x97\x04\n\x07\x43ommand\x12\r\n\x05magic\x18\x01 \x01(\x05\x12\x1c\n\x04\x65xec\x18\x02 \x01(\x0b\x32\x0c.rpc.CmdExecH\x00\x12 \n\x06\x64lopen\x18\x03 \x01(\x0b\x32\x0e.rpc.CmdDlopenH\x00\x12\"\n\x07\x64lclose\x18\x04 \x01(\x0b\x32\x0f.rpc.CmdDlcloseH\x00\x12\x1e\n\x05\x64lsym\x18\x05 \x01(\x0b\x32\r.rpc.CmdDlsymH\x00\x12\x1c\n\x04\x63\x61ll\x18\x06 \x01(\x0b\x32\x0c.rpc.CmdCallH\x00\x12\x1c\n\x04peek\x18\x07 \x01(\x0b\x32\x0c.rpc.CmdPeekH\x00\x12\x1c\n\x04poke\x18\x08 \x01(\x0b\x32\x0c.rpc.CmdPokeH\x00\x12#\n\x08list_dir\x18\t \x01(\x0b\x32\x0f.rpc.CmdListDirH\x00\x12)\n\x0bshow_object\x18\n \x01(\x0b\x32\x12.rpc.CmdShowObjectH\x00\x12\'\n\nshow_class\x18\x0b \x01(\x0b\x32\x11.rpc.CmdShowClassH\x00\x12)\n\x0b\x64ummy_block\x18\x0c \x01(\x0b\x32\x12.rpc.CmdDummyBlockH\x00\x12\x1e\n\x05\x63lose\x18\r \x01(\x0b\x32\r.rpc.CmdCloseH\x00\x12*\n\nclass_list\x18\x0e \x01(\x0b\x32\x14.rpc.CmdGetClassListH\x00\x12\'\n\nexec_chunk\x18\x0f \x01(\x0b\x32\x11.rpc.CmdExecChunkH\x00\x42\x06\n\x04type\"\xd5\x04\n\x08Response\x12$\n\x04\x65xec\x18\x01 \x01(\x0b\x32\x14.rpc.ResponseCmdExecH\x00\x12/\n\nexec_chunk\x18\x02 \x01(\x0b\x32\x19.rpc.ResponseCmdExecChunkH\x00\x12%\n\x06\x64lopen\x18\x03 \x01(\x0b\x32\x13.rpc.ResponseDlopenH\x00\x12\'\n\x07\x64lclose\x18\x04 \x01(\x0b\x32\x14.rpc.ResponseDlcloseH\x00\x12#\n\x05\x64lsym\x18\x05 \x01(\x0b\x32\x12.rpc.ResponseDlsymH\x00\x12!\n\x04peek\x18\x06 \x01(\x0b\x32\x11.rpc.ResponsePeekH\x00\x12!\n\x04poke\x18\x07 \x01(\x0b\x32\x11.rpc.ResponsePokeH\x00\x12!\n\x04\x63\x61ll\x18\x08 \x01(\x0b\x32\x11.rpc.ResponseCallH\x00\x12#\n\x05\x65rror\x18\t \x01(\x0b\x32\x12.rpc.ResponseErrorH\x00\x12.\n\x0b\x64ummy_block\x18\n \x01(\x0b\x32\x17.rpc.ResponseDummyBlockH\x00\x12.\n\x0bshow_object\x18\x0b \x01(\x0b\x32\x17.rpc.ResponseShowObjectH\x00\x12/\n\nclass_list\x18\x0c \x01(\x0b\x32\x19.rpc.ResponseGetClassListH\x00\x12,\n\nshow_class\x18\r \x01(\x0b\x32\x16.rpc.ResponseShowClassH\x00\x12(\n\x08list_dir\x18\x0e \x01(\x0b\x32\x14.rpc.ResponseListdirH\x00\x42\x06\n\x04type\"\xd4\x01\n\x12ReturnRegistersArm\x12\n\n\x02x0\x18\x01 \x01(\x04\x12\n\n\x02x1\x18\x02 \x01(\x04\x12\n\n\x02x2\x18\x03 \x01(\x04\x12\n\n\x02x3\x18\x04 \x01(\x04\x12\n\n\x02x4\x18\x05 \x01(\x04\x12\n\n\x02x5\x18\x06 \x01(\x04\x12\n\n\x02x6\x18\x07 \x01(\x04\x12\n\n\x02x7\x18\x08 \x01(\x04\x12\n\n\x02\x64\x30\x18\t \x01(\x01\x12\n\n\x02\x64\x31\x18\n \x01(\x01\x12\n\n\x02\x64\x32\x18\x0b \x01(\x01\x12\n\n\x02\x64\x33\x18\x0c \x01(\x01\x12\n\n\x02\x64\x34\x18\r \x01(\x01\x12\n\n\x02\x64\x35\x18\x0e \x01(\x01\x12\n\n\x02\x64\x36\x18\x0f \x01(\x01\x12\n\n\x02\x64\x37\x18\x10 \x01(\x01\"[\n\x08\x41rgument\x12\x0f\n\x05v_int\x18\x01 \x01(\x04H\x00\x12\x12\n\x08v_double\x18\x02 \x01(\x01H\x00\x12\x0f\n\x05v_str\x18\x03 \x01(\tH\x00\x12\x11\n\x07v_bytes\x18\x04 \x01(\x0cH\x00\x42\x06\n\x04type\"U\n\tHandshake\x12\r\n\x05magic\x18\x01 \x01(\r\x12\x17\n\x04\x61rch\x18\x02 \x01(\x0e\x32\t.rpc.Arch\x12\x0f\n\x07sysname\x18\x03 \x01(\t\x12\x0f\n\x07machine\x18\x04 \x01(\t\"*\n\tObjcClass\x12\x0f\n\x07\x61\x64\x64ress\x18\x01 \x01(\x04\x12\x0c\n\x04name\x18\x02 \x01(\t\" \n\rCmdShowObject\x12\x0f\n\x07\x61\x64\x64ress\x18\x01 \x01(\x04\")\n\x12ResponseShowObject\x12\x13\n\x0b\x64\x65scription\x18\x01 \x01(\t\"\x1f\n\x0c\x43mdShowClass\x12\x0f\n\x07\x61\x64\x64ress\x18\x01 \x01(\x04\"(\n\x11ResponseShowClass\x12\x13\n\x0b\x64\x65scription\x18\x01 \x01(\t\"\x1e\n\x0c\x43mdExecChunk\x12\x0e\n\x06\x62uffer\x18\x01 \x01(\x0c\"E\n\x14ResponseCmdExecChunk\x12\x10\n\x06\x62uffer\x18\x01 \x01(\x0cH\x00\x12\x13\n\texit_code\x18\x02 \x01(\rH\x00\x42\x06\n\x04type\"+\n\tCmdDlopen\x12\x10\n\x08\x66ilename\x18\x01 \x01(\t\x12\x0c\n\x04mode\x18\x02 \x01(\x05\" \n\x0eResponseDlopen\x12\x0e\n\x06handle\x18\x01 \x01(\x04\"\x1c\n\nCmdDlclose\x12\x0e\n\x06handle\x18\x01 \x01(\x04\"\x1e\n\x0fResponseDlclose\x12\x0b\n\x03res\x18\x01 \x01(\r\"/\n\x08\x43mdDlsym\x12\x0e\n\x06handle\x18\x01 \x01(\x04\x12\x13\n\x0bsymbol_name\x18\x02 \x01(\t\"\x1c\n\rResponseDlsym\x12\x0b\n\x03ptr\x18\x01 \x01(\x04\"9\n\x07\x43mdExec\x12\x12\n\nbackground\x18\x01 \x01(\x08\x12\x0c\n\x04\x61rgv\x18\x02 \x03(\t\x12\x0c\n\x04\x65nvp\x18\x03 \x03(\t\"\x1e\n\x0fResponseCmdExec\x12\x0b\n\x03pid\x18\x01 \x01(\r\"N\n\x07\x43mdCall\x12\x0f\n\x07\x61\x64\x64ress\x18\x01 \x01(\x04\x12\x15\n\rva_list_index\x18\x02 \x01(\x04\x12\x1b\n\x04\x61rgv\x18\x03 \x03(\x0b\x32\r.rpc.Argument\"i\n\x0cResponseCall\x12\x30\n\rarm_registers\x18\x01 \x01(\x0b\x32\x17.rpc.ReturnRegistersArmH\x00\x12\x16\n\x0creturn_value\x18\x02 \x01(\x04H\x00\x42\x0f\n\rreturn_values\"(\n\x07\x43mdPeek\x12\x0f\n\x07\x61\x64\x64ress\x18\x01 \x01(\x04\x12\x0c\n\x04size\x18\x02 \x01(\x04\"\x1c\n\x0cResponsePeek\x12\x0c\n\x04\x64\x61ta\x18\x01 \x01(\x0c\"(\n\x07\x43mdPoke\x12\x0f\n\x07\x61\x64\x64ress\x18\x01 \x01(\x04\x12\x0c\n\x04\x64\x61ta\x18\x02 \x01(\x0c\"\x1e\n\x0cResponsePoke\x12\x0e\n\x06result\x18\x01 \x01(\x04\"\x1a\n\nCmdListDir\x12\x0c\n\x04path\x18\x01 \x01(\t\"\x0f\n\rCmdDummyBlock\"3\n\x12ResponseDummyBlock\x12\x0f\n\x07\x61\x64\x64ress\x18\x01 \x01(\x04\x12\x0c\n\x04size\x18\x02 \x01(\x04\"\x11\n\x0f\x43mdGetClassList\"7\n\x14ResponseGetClassList\x12\x1f\n\x07\x63lasses\x18\x01 \x03(\x0b\x32\x0e.rpc.ObjcClass\"\"\n\rResponseError\x12\x11\n\tfunc_name\x18\x01 \x01(\t\"R\n\x0fResponseListdir\x12\r\n\x05magic\x18\x01 \x01(\x04\x12\x0c\n\x04\x64irp\x18\x02 \x01(\x04\x12\"\n\x0b\x64ir_entries\x18\x03 \x03(\x0b\x32\r.rpc.DirEntry\"m\n\x08\x44irEntry\x12\x0e\n\x06\x64_type\x18\x01 \x01(\x04\x12\x0e\n\x06\x64_name\x18\x02 \x01(\t\x12 \n\x05lstat\x18\x03 \x01(\x0b\x32\x11.rpc.DirEntryStat\x12\x1f\n\x04stat\x18\x04 \x01(\x0b\x32\x11.rpc.DirEntryStat\"\x83\x02\n\x0c\x44irEntryStat\x12\x0e\n\x06\x65rrno1\x18\x01 \x01(\x04\x12\x0e\n\x06st_dev\x18\x02 \x01(\x04\x12\x0f\n\x07st_mode\x18\x03 \x01(\x04\x12\x10\n\x08st_nlink\x18\x04 \x01(\x04\x12\x0e\n\x06st_ino\x18\x05 \x01(\x04\x12\x0e\n\x06st_uid\x18\x06 \x01(\x04\x12\x0e\n\x06st_gid\x18\x07 \x01(\x04\x12\x0f\n\x07st_rdev\x18\x08 \x01(\x04\x12\x0f\n\x07st_size\x18\t \x01(\x04\x12\x11\n\tst_blocks\x18\n \x01(\x04\x12\x12\n\nst_blksize\x18\x0b \x01(\x04\x12\x11\n\tst_atime1\x18\x0c \x01(\x04\x12\x11\n\tst_mtime1\x18\r \x01(\x04\x12\x11\n\tst_ctime1\x18\x0e \x01(\x04\"\n\n\x08\x43mdClose*(\n\x04\x41rch\x12\x10\n\x0c\x41RCH_UNKNOWN\x10\x00\x12\x0e\n\nARCH_ARM64\x10\x01\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'rpc_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_ARCH']._serialized_start=3173
  _globals['_ARCH']._serialized_end=3213
  _globals['_COMMAND']._serialized_start=19
  _globals['_COMMAND']._serialized_end=554
  _globals['_RESPONSE']._serialized_start=557
  _globals['_RESPONSE']._serialized_end=1154
  _globals['_RETURNREGISTERSARM']._serialized_start=1157
  _globals['_RETURNREGISTERSARM']._serialized_end=1369
  _globals['_ARGUMENT']._serialized_start=1371
  _globals['_ARGUMENT']._serialized_end=1462
  _globals['_HANDSHAKE']._serialized_start=1464
  _globals['_HANDSHAKE']._serialized_end=1549
  _globals['_OBJCCLASS']._serialized_start=1551
  _globals['_OBJCCLASS']._serialized_end=1593
  _globals['_CMDSHOWOBJECT']._serialized_start=1595
  _globals['_CMDSHOWOBJECT']._serialized_end=1627
  _globals['_RESPONSESHOWOBJECT']._serialized_start=1629
  _globals['_RESPONSESHOWOBJECT']._serialized_end=1670
  _globals['_CMDSHOWCLASS']._serialized_start=1672
  _globals['_CMDSHOWCLASS']._serialized_end=1703
  _globals['_RESPONSESHOWCLASS']._serialized_start=1705
  _globals['_RESPONSESHOWCLASS']._serialized_end=1745
  _globals['_CMDEXECCHUNK']._serialized_start=1747
  _globals['_CMDEXECCHUNK']._serialized_end=1777
  _globals['_RESPONSECMDEXECCHUNK']._serialized_start=1779
  _globals['_RESPONSECMDEXECCHUNK']._serialized_end=1848
  _globals['_CMDDLOPEN']._serialized_start=1850
  _globals['_CMDDLOPEN']._serialized_end=1893
  _globals['_RESPONSEDLOPEN']._serialized_start=1895
  _globals['_RESPONSEDLOPEN']._serialized_end=1927
  _globals['_CMDDLCLOSE']._serialized_start=1929
  _globals['_CMDDLCLOSE']._serialized_end=1957
  _globals['_RESPONSEDLCLOSE']._serialized_start=1959
  _globals['_RESPONSEDLCLOSE']._serialized_end=1989
  _globals['_CMDDLSYM']._serialized_start=1991
  _globals['_CMDDLSYM']._serialized_end=2038
  _globals['_RESPONSEDLSYM']._serialized_start=2040
  _globals['_RESPONSEDLSYM']._serialized_end=2068
  _globals['_CMDEXEC']._serialized_start=2070
  _globals['_CMDEXEC']._serialized_end=2127
  _globals['_RESPONSECMDEXEC']._serialized_start=2129
  _globals['_RESPONSECMDEXEC']._serialized_end=2159
  _globals['_CMDCALL']._serialized_start=2161
  _globals['_CMDCALL']._serialized_end=2239
  _globals['_RESPONSECALL']._serialized_start=2241
  _globals['_RESPONSECALL']._serialized_end=2346
  _globals['_CMDPEEK']._serialized_start=2348
  _globals['_CMDPEEK']._serialized_end=2388
  _globals['_RESPONSEPEEK']._serialized_start=2390
  _globals['_RESPONSEPEEK']._serialized_end=2418
  _globals['_CMDPOKE']._serialized_start=2420
  _globals['_CMDPOKE']._serialized_end=2460
  _globals['_RESPONSEPOKE']._serialized_start=2462
  _globals['_RESPONSEPOKE']._serialized_end=2492
  _globals['_CMDLISTDIR']._serialized_start=2494
  _globals['_CMDLISTDIR']._serialized_end=2520
  _globals['_CMDDUMMYBLOCK']._serialized_start=2522
  _globals['_CMDDUMMYBLOCK']._serialized_end=2537
  _globals['_RESPONSEDUMMYBLOCK']._serialized_start=2539
  _globals['_RESPONSEDUMMYBLOCK']._serialized_end=2590
  _globals['_CMDGETCLASSLIST']._serialized_start=2592
  _globals['_CMDGETCLASSLIST']._serialized_end=2609
  _globals['_RESPONSEGETCLASSLIST']._serialized_start=2611
  _globals['_RESPONSEGETCLASSLIST']._serialized_end=2666
  _globals['_RESPONSEERROR']._serialized_start=2668
  _globals['_RESPONSEERROR']._serialized_end=2702
  _globals['_RESPONSELISTDIR']._serialized_start=2704
  _globals['_RESPONSELISTDIR']._serialized_end=2786
  _globals['_DIRENTRY']._serialized_start=2788
  _globals['_DIRENTRY']._serialized_end=2897
  _globals['_DIRENTRYSTAT']._serialized_start=2900
  _globals['_DIRENTRYSTAT']._serialized_end=3159
  _globals['_CMDCLOSE']._serialized_start=3161
  _globals['_CMDCLOSE']._serialized_end=3171
# @@protoc_insertion_point(module_scope)
