import struct
import threading

from rpcclient.exceptions import InvalidServerVersionMagicError, ResponseNotFoundError, ServerDiedError, \
    ServerResponseError
from rpcclient.protos.rpc_pb2 import CmdClose, Command, Handshake, Response

# field[0] is MAGIC - skip
COMMAND_MAPPING = {field.message_type.name: field.name for field in Command.DESCRIPTOR.fields[1:]}
DEFAULT_PORT = 5910
SERVER_MAGIC_VERSION = 0x88888807
MAGIC = 0x12345678
MAX_PATH_LEN = 1024


class ProtoSocket:
    def __init__(self, sock):
        self.handshake = None
        self._sock = sock
        self._protocol_lock = threading.Lock()
        self._do_handshake()

    def _do_handshake(self):
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
        if response.HasField(command_type):
            return getattr(response, command_type.lower(), None)
        elif response.HasField('error'):
            raise ServerResponseError(response.error)
        else:
            raise ResponseNotFoundError()
        # Handle unrecognized command or return a default response

    def _receive(self):
        try:
            size = struct.unpack('<Q', self._sock.recv(8))[0]
            buff = self._recvall(size)
            return size, buff
        except struct.error:
            raise ConnectionError()

    def _send(self, message) -> None:
        buff = struct.pack('<Q', len(message)) + message
        self._sock.sendall(buff)

    def _recvall(self, size: int) -> bytes:
        buf = b''
        while size:
            try:
                chunk = self._sock.recv(size)
            except BlockingIOError:
                continue
            if self._sock.gettimeout() == 0 and not chunk:
                # TODO: replace self._sock.gettimeout() == 0 on -> self._sock.getblocking() on python37+
                raise ServerDiedError()
            size -= len(chunk)
            buf += chunk
        return buf

    def close(self):
        command = Command(magic=MAGIC, close=CmdClose())
        self._send(command.SerializeToString())
        self._sock.close()

    @staticmethod
    def hex_dump(data):
        hex_data = ' '.join([format(byte, '02X') for byte in data])
        print(hex_data)
