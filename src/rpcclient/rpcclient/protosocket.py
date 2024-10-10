import socket
import struct
import threading

from rpcclient.exceptions import InvalidServerVersionMagicError, ServerDiedError, ServerResponseError
from rpcclient.protos.rpc_pb2 import CmdClose, Command, Handshake, Response

# field[0] is MAGIC - skip
COMMAND_MAPPING = {field.message_type.name: field.name for field in Command.DESCRIPTOR.fields[1:]}
SERVER_MAGIC_VERSION = 0x88888809
MAGIC = 0x12345679
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
        if self.handshake.magic != SERVER_MAGIC_VERSION:
            raise InvalidServerVersionMagicError(f'got {self.handshake.magic:x} instead of {SERVER_MAGIC_VERSION:x}')

    def send_recv(self, sub_command):
        command = Command(magic=MAGIC, **{COMMAND_MAPPING.get(sub_command.DESCRIPTOR.name): sub_command})
        response = Response()
        with self._protocol_lock:
            self._send(command.SerializeToString())
            size, buff = self._receive()
        command_type = command.WhichOneof('type')
        response.ParseFromString(buff)

        # Iterate through all possible response types
        if response.HasField('error'):
            raise ServerResponseError(response.error)
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
        command = Command(magic=MAGIC, close=CmdClose())
        self._send(command.SerializeToString())
        self.raw_socket.close()
