"""
This module makes sure imports from the *_pb2 modules don't depend on the locally installed protobuf version
"""
import os

os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
os.environ['TEMPORARILY_DISABLE_PROTOBUF_VERSION_CHECK'] = 'true'

from rpcclient.protos.rpc_pb2 import ARCH_ARM64, Argument, CmdCall, CmdClose, CmdCustom, CmdDlclose, CmdDlopen, \
    CmdDlsym, CmdDummyBlock, CmdExec, CmdGetClassList, CmdListDir, CmdPeek, CmdPoke, CmdShowClass, CmdShowObject, \
    Command, Handshake, Response, ResponseCustom  # noqa: E402

__all__ = ['Argument', 'CmdCall', 'CmdClose', 'CmdDlclose', 'CmdDlopen', 'CmdDlsym', 'CmdDummyBlock', 'CmdExec',
           'CmdGetClassList', 'CmdListDir', 'CmdPeek', 'CmdPoke', 'CmdShowClass', 'CmdShowObject', 'Command',
           'Handshake', 'Response', 'ARCH_ARM64', 'CmdCustom', 'ResponseCustom']
