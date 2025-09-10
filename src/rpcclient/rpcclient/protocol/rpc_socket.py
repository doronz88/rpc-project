import logging
import struct
import threading
from socket import socket

from rpcclient.exceptions import ServerDiedError
from rpcclient.protos.rpc_pb2 import Handshake, ProtocolConstants, RpcMessage, RpcPtyMessage

logger = logging.getLogger(__name__)


class RpcSocket:
    """
    Facilitates communication with a remote server using sockets and implements
    specific RPC (Remote Procedure Call) messaging protocols.

    This class provides methods to send and receive RPC messages, ensuring
    correct serialization and deserialization of messages. Additionally, it
    manages a protocol lock for synchronized message send and receive operations
    where applicable.

    Attributes:
        raw_socket: The underlying socket used for communication with the remote server.
    """
    def __init__(self, sock: socket):
        self.raw_socket = sock
        self._protocol_lock = threading.Lock()

    def _msg_recv(self) -> bytes:
        try:
            size = struct.unpack('<Q', self.raw_socket.recv(8))[0]
            buff = self._recvall(size)
            return buff
        except struct.error:
            raise ConnectionError()

    def _msg_send(self, message: bytes) -> None:
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

    def rpc_handshake_recv(self):
        rpc_handshake = Handshake()
        rpc_handshake.ParseFromString(self._msg_recv())
        return rpc_handshake

    def rpc_msg_recv(self):
        rpc_msg = RpcMessage()
        rpc_msg.ParseFromString(self._msg_recv())
        return rpc_msg

    def rpc_msg_recv_pty(self):
        rpc_msg = RpcPtyMessage()
        rpc_msg.ParseFromString(self._msg_recv())
        return rpc_msg

    def rpc_msg_send(self, msg: RpcMessage) -> None:
        msg.magic = ProtocolConstants.MESSAGE_MAGIC
        rpc_msg = msg.SerializeToString()
        self._msg_send(rpc_msg)

    def rpc_msg_send_recv(self, msg: RpcMessage) -> RpcMessage:
        with self._protocol_lock:
            self.rpc_msg_send(msg)
            return self.rpc_msg_recv()
