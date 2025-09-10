import logging
import socket
from typing import Optional

from rpcclient.exceptions import InvalidServerVersionMagicError, ServerResponseError
from rpcclient.protocol.messages import RpcMessageRegistry
from rpcclient.protocol.rpc_socket import RpcSocket
from rpcclient.protos.rpc_pb2 import Handshake, ProtocolConstants, RpcMessage

logger = logging.getLogger(__name__)

BASIC_MESSAGES = RpcMessageRegistry(modules=['rpcclient.protos.rpc_api_pb2'])


class RpcBridge:
    def __init__(self, sock: socket.socket, messages: Optional[RpcMessageRegistry] = None) -> None:
        # Maps request class -> binding
        self.messages: RpcMessageRegistry = messages or BASIC_MESSAGES.clone()
        self.handshake: Optional[Handshake] = None
        self.sock = RpcSocket(sock)

        self._do_handshake()

    def rpc_call(self, msg_id: int, **kwargs):
        """
        Resolve msg_id/reply class from request_msg's type, build RpcMessage, send and, parse reply.
        """
        req = self.messages.get(msg_id)(**kwargs)
        msg = RpcMessage(
            client_id=self.handshake.client_id,
            msg_id=msg_id,
            payload=req.SerializeToString(),
        )
        rep_msg = self.sock.rpc_msg_send_recv(msg)
        rep = self.messages.get(rep_msg.msg_id)()
        rep.ParseFromString(rep_msg.payload)
        if rep_msg.msg_id == ProtocolConstants.REP_ERROR:
            logger.error(f'Server error: {rep.message}')
            raise ServerResponseError(rep.errno_code, rep.message)
        return rep

    def _do_handshake(self) -> None:
        self.handshake = self.sock.rpc_handshake_recv()
        if self.handshake.server_version != ProtocolConstants.SERVER_VERSION:
            raise InvalidServerVersionMagicError(
                f'got {self.handshake.magic:x} instead of {ProtocolConstants.SERVER_VERSION:x}')

    def close(self) -> None:
        self.sock.raw_socket.close()
