import socket
import struct
import threading

from google.protobuf.descriptor import FieldDescriptor

from rpcclient.core.protobuf_bridge import CmdClose, Command, Handshake, Response
from rpcclient.exceptions import InvalidServerVersionMagicError, ServerDiedError, ServerResponseError
from rpcclient.protos.rpc_pb2 import ErrorCode, ProtocolConstants

COMMAND_MAPPING = {field.message_type.name: field.name for field in Command.DESCRIPTOR.fields if
                   field.type == FieldDescriptor.TYPE_MESSAGE}
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

    def send_recv(self, sub_command, client_id: int):
        command = Command(magic=ProtocolConstants.MESSAGE_MAGIC, client_id=client_id,
                          **{COMMAND_MAPPING.get(sub_command.DESCRIPTOR.name): sub_command})
        response = Response()
        with self._protocol_lock:
            self._send(command.SerializeToString())
            size, buff = self._receive()
        command_type = command.WhichOneof('type')
        response.ParseFromString(buff)

        # Iterate through all possible response types
        if response.HasField('error'):
            if response.error.code == ErrorCode.ERROR_UNSUPPORTED_COMMAND:
                raise ServerResponseError(f'Command "{command_type}" is not supported by server')
            else:
                raise ServerResponseError(f'Command "{command_type}" failed: {response.error}')
        else:
            return getattr(response, command_type.lower())

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
