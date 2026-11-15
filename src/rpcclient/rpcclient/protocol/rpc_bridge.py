import logging
import socket
import subprocess
from typing import Any, final
from typing_extensions import Self

from google.protobuf.message import Message

from rpcclient.exceptions import InvalidServerVersionMagicError, ServerResponseError
from rpcclient.protocol.messages import resolve_request
from rpcclient.protocol.rpc_socket import RpcSocket
from rpcclient.protos.rpc_api_pb2 import ReplyError
from rpcclient.protos.rpc_pb2 import ProtocolConstants, RpcMessage


logger = logging.getLogger(__name__)


def _has_process_exited(process: subprocess.Popen) -> bool:
    return process.poll() is not None


class RpcBridge:
    @final
    def __init__(
        self,
        sock: RpcSocket,
        client_id: int,
        platform_name: str,
        arch: int,
        sysname: str,
        owns_socket: bool = True,
        local_process: subprocess.Popen | None = None,
    ) -> None:
        self.sock: RpcSocket = sock
        self.client_id: int = client_id
        self.platform: str = platform_name
        self.arch: int = arch
        self.sysname: str = sysname
        self._owns_socket: bool = owns_socket
        self._local_process: subprocess.Popen | None = local_process

    @classmethod
    async def connect(cls, raw_sock: socket.socket) -> Self:
        sock = RpcSocket(raw_sock)
        handshake = await sock.rpc_handshake_recv()
        if handshake.server_version != ProtocolConstants.SERVER_VERSION:
            raise InvalidServerVersionMagicError(
                f"got {handshake.magic:x} instead of {ProtocolConstants.SERVER_VERSION:x}"
            )
        return cls(sock, handshake.client_id, handshake.platform.lower(), handshake.arch, handshake.sysname.lower())

    async def rpc_call(self, request: Message) -> Any:
        """
        Resolve msg_id/reply class from the request's type, build RpcMessage, send and, parse reply.
        """
        msg_id, reply_class = resolve_request(type(request))
        msg = RpcMessage(
            client_id=self.client_id,
            msg_id=msg_id,
            payload=request.SerializeToString(),
        )

        rep_msg = await self.sock.rpc_msg_send_recv(msg)
        if rep_msg.msg_id == ProtocolConstants.REP_ERROR:
            error = ReplyError()
            error.ParseFromString(rep_msg.payload)
            logger.error(f"Server error: {error.message}")
            raise ServerResponseError(error.message)

        elif rep_msg.msg_id != msg_id + ProtocolConstants.RPC_MAX_REQ_MSG_ID:
            raise ValueError(f"Unexpected reply msg_id {rep_msg.msg_id} to {request.DESCRIPTOR.full_name}")

        rep = reply_class()
        rep.ParseFromString(rep_msg.payload)
        return rep

    def close(self) -> None:
        if not self._owns_socket:
            raise RuntimeError("socket is owned by another client")
        try:
            self.sock.raw_socket.close()
        finally:
            self._terminate_local_process()

    def set_local_process(self, process: subprocess.Popen) -> None:
        self._local_process = process

    def _terminate_local_process(self) -> None:
        process = self._local_process
        self._local_process = None
        if process is None or _has_process_exited(process):
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    def clone(self) -> Self:
        return type(self)(self.sock, self.client_id, self.platform, self.arch, self.sysname, owns_socket=False)
