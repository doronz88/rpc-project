import logging
import socket
from typing import Optional

from rpcclient.exceptions import InvalidServerVersionMagicError, ServerResponseError
from rpcclient.protocol.messages import RpcMessageRegistry
from rpcclient.protocol.rpc_socket import RpcSocket
from rpcclient.protos.rpc_pb2 import ProtocolConstants, RpcMessage

logger = logging.getLogger(__name__)

BASIC_MESSAGES = RpcMessageRegistry(modules=['rpcclient.protos.rpc_api_pb2'])


class RpcBridge:
    def __init__(self, sock: RpcSocket, client_id: int, platform_name: str,
                 arch: int, sysname: str, messages: Optional[RpcMessageRegistry] = None,
                 owns_socket: bool = True) -> None:
        self.messages: RpcMessageRegistry = messages or BASIC_MESSAGES.clone()
        self.sock = sock
        self.client_id = client_id
        self.platform = platform_name
        self.arch = arch
        self.sysname = sysname
        self._owns_socket = owns_socket

    @classmethod
    def connect(cls, raw_sock: socket.socket, messages: Optional[RpcMessageRegistry] = None) -> "RpcBridge":
        sock = RpcSocket(raw_sock)
        handshake = sock.rpc_handshake_recv()
        if handshake.server_version != ProtocolConstants.SERVER_VERSION:
            raise InvalidServerVersionMagicError(
                f'got {handshake.magic:x} instead of {ProtocolConstants.SERVER_VERSION:x}'
            )
        return cls(sock, handshake.client_id, handshake.platform.lower(), handshake.arch, handshake.sysname.lower(), messages)

    def rpc_call(self, msg_id: int, **kwargs):
        """
        Resolve msg_id/reply class from request_msg's type, build RpcMessage, send and, parse reply.
        """
        req = self.messages.get(msg_id)(**kwargs)
        msg = RpcMessage(
            client_id=self.client_id,
            msg_id=msg_id,
            payload=req.SerializeToString(),
        )
        rep_msg = self.sock.rpc_msg_send_recv(msg)
        rep = self.messages.get(rep_msg.msg_id)()
        rep.ParseFromString(rep_msg.payload)
        if rep_msg.msg_id == ProtocolConstants.REP_ERROR:
            logger.error(f'Server error: {rep.message}')
            raise ServerResponseError(rep.message)
        return rep

    def close(self) -> None:
        if not self._owns_socket:
            raise RuntimeError('socket is owned by another client')
        self.sock.raw_socket.close()

    def clone(self) -> 'RpcBridge':
        return RpcBridge(self.sock, self.client_id, self.platform,
                         self.arch, self.sysname, self.messages.clone(),
                         owns_socket=False)
