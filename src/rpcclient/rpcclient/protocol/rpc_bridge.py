import logging
import socket
from typing import Optional

from cached_property import cached_property

from rpcclient.exceptions import InvalidServerVersionMagicError, ServerResponseError
from rpcclient.protocol.messages import RpcMessageRegistry
from rpcclient.protocol.rpc_socket import RpcSocket
from rpcclient.protos.rpc_pb2 import Handshake, ProtocolConstants, RpcMessage

logger = logging.getLogger(__name__)

BASIC_MESSAGES = RpcMessageRegistry(modules=['rpcclient.protos.rpc_api_pb2'])


class RpcBridge:
    def __init__(self, sock: RpcSocket, handshake: Handshake, messages: Optional[RpcMessageRegistry] = None) -> None:
        self.messages: RpcMessageRegistry = messages or BASIC_MESSAGES.clone()
        self._handshake = handshake
        self.sock = sock

    @classmethod
    def connect(cls, raw_sock: socket.socket, messages: Optional[RpcMessageRegistry] = None) -> "RpcBridge":
        sock = RpcSocket(raw_sock)
        handshake = sock.rpc_handshake_recv()
        if handshake.server_version != ProtocolConstants.SERVER_VERSION:
            raise InvalidServerVersionMagicError(
                f'got {handshake.magic:x} instead of {ProtocolConstants.SERVER_VERSION:x}'
            )
        return cls(sock, handshake, messages)

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
        self.sock.raw_socket.close()

    @cached_property
    def client_id(self) -> int:
        return self._handshake.client_id

    @cached_property
    def platform(self) -> str:
        return self._handshake.platform.lower()

    @cached_property
    def sysname(self) -> str:
        return self._handshake.sysname.lower()

    @cached_property
    def arch(self) -> int:
        return self._handshake.arch
