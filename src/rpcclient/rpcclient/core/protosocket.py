import socket
import struct
import threading

from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message

from rpcclient.core.protobuf_bridge import CmdClose, Command, Handshake, Response
from rpcclient.exceptions import InvalidServerVersionMagicError, ServerDiedError, ServerResponseError
from rpcclient.protos.rpc_pb2 import ProtocolConstants, CommandId, CmdDlopen, CmdDlclose, CmdDlsym, CmdExec, \
    CmdCall, CmdPeek, CmdPoke, CmdListDir, CmdShowObject, CmdShowClass, CmdDummyBlock, CmdGetClassList, CmdExecChunk, \
    ResponseDlopen, ResponseDlclose, ResponseDlsym, ResponseCall, ResponsePeek, ResponsePoke, StatusCode

COMMAND_MAPPING = {
    CommandId.CMD_DLOPEN: 'CmdDlopen',
    CommandId.CMD_DLCLOSE: 'CmdDlclose',
    CommandId.CMD_DLSYM: 'CmdDlsym',
    CommandId.CMD_EXEC: 'CmdExec',
    CommandId.CMD_CALL: 'CmdCall',
    CommandId.CMD_PEEK: 'CmdPeek',
    CommandId.CMD_POKE: 'CmdPoke',
    CommandId.CMD_LIST_DIR: 'CmdListDir',
    CommandId.CMD_SHOW_OBJECT: 'CmdShowObject',
    CommandId.CMD_SHOW_CLASS: 'CmdShowClass',
    CommandId.CMD_DUMMY_BLOCK: 'CmdDummyBlock',
    CommandId.CMD_GET_CLASS_LIST: 'CmdGetClassList',
    CommandId.CMD_EXEC_CHUNK: 'CmdExecChunk',
}

RESPONSE_MAPPING = {
    CommandId.CMD_DLOPEN: ResponseDlopen,
    CommandId.CMD_DLCLOSE: ResponseDlclose,
    CommandId.CMD_DLSYM: ResponseDlsym,
    CommandId.CMD_CALL: ResponseCall,
    CommandId.CMD_PEEK: ResponsePeek,
    CommandId.CMD_POKE: ResponsePoke,
}
CLASS_TO_COMMAND_ID = {v: k for k, v in COMMAND_MAPPING.items()}

MAX_PATH_LEN = 1024


class ProtoSocket:
    def __init__(self, sock: socket.socket):
        self.handshake = None
        self.raw_socket = sock
        self._protocol_lock = threading.Lock()
        self._do_handshake()

    def _do_handshake(self) -> None:
        self.handshake = Handshake()
        size, buff = self._receive()
        self.handshake.ParseFromString(buff)
        if self.handshake.magic != ProtocolConstants.SERVER_VERSION:
            raise InvalidServerVersionMagicError(
                f'got {self.handshake.magic:x} instead of {ProtocolConstants.SERVER_VERSION:x}')
        self.client_id = self.handshake.client_id

    def send_recv(self, sub_command: Message, client_id: int):
        class_name = sub_command.__class__.__name__
        cmd_id = CLASS_TO_COMMAND_ID.get(class_name)

        if cmd_id is None:
            raise ValueError(f"Unknown command class: {class_name}")

        command = Command(
            magic=ProtocolConstants.MESSAGE_MAGIC,
            client_id=client_id,
            cmd_id=cmd_id,
            payload=sub_command.SerializeToString()
        )
        response = Response()
        with self._protocol_lock:
            self._send(command.SerializeToString())
            size, buff = self._receive()
        response.ParseFromString(buff)

        # Iterate through all possible response types
        if response.code == StatusCode.OK:
            inner = RESPONSE_MAPPING.get(cmd_id)()
            inner.ParseFromString(response.payload)
            return inner

        if response.error == StatusCode.UNSUPPORTED_COMMAND:
            raise ServerResponseError(f'Command "{cmd_id}" is not supported by server')
        else:
            raise ServerResponseError(f'Command "{cmd_id}" failed: {response.error}')

    def _receive(self) -> tuple[int, bytes]:
        try:
            size = struct.unpack('<Q', self.raw_socket.recv(8))[0]
            buff = self._recvall(size)
            return size, buff
        except struct.error:
            raise ConnectionError()

    def _send(self, message: bytes) -> None:
        buff = struct.pack('<Q', len(message)) + message
        self.raw_socket.sendall(buff)

    def _recvall(self, size: int) -> bytes:
        buf = b''
        while size:
            try:
                chunk = self.raw_socket.recv(size)
            except BlockingIOError:
                continue
            if not self.raw_socket.getblocking() and not chunk:
                raise ServerDiedError()
            size -= len(chunk)
            buf += chunk
        return buf

    def close(self) -> None:
        command = Command(magic=ProtocolConstants.MESSAGE_MAGIC, client_id=self.handshake.client_id, close=CmdClose())
        self._send(command.SerializeToString())
        self.raw_socket.close()
