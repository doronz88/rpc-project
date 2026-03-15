import abc
import logging
import socket
from typing import Any, Generic, TypeVar, final
from typing_extensions import Self

import zyncio

from rpcclient.exceptions import InvalidServerVersionMagicError, ServerResponseError
from rpcclient.protocol.messages import RpcMessageRegistry
from rpcclient.protocol.rpc_socket import AsyncRpcSocket, SyncRpcSocket
from rpcclient.protos.rpc_pb2 import ProtocolConstants, RpcMessage


logger = logging.getLogger(__name__)

BASIC_MESSAGES = RpcMessageRegistry(modules=["rpcclient.protos.rpc_api_pb2"])


RpcSocketT = TypeVar("RpcSocketT", SyncRpcSocket, AsyncRpcSocket)


class RpcBridge(Generic[RpcSocketT], abc.ABC):
    @final
    def __init__(
        self,
        sock: RpcSocketT,
        client_id: int,
        platform_name: str,
        arch: int,
        sysname: str,
        messages: RpcMessageRegistry | None = None,
        owns_socket: bool = True,
    ) -> None:
        self.messages: RpcMessageRegistry = messages or BASIC_MESSAGES.clone()
        self.sock: RpcSocketT = sock
        self.client_id: int = client_id
        self.platform: str = platform_name
        self.arch: int = arch
        self.sysname: str = sysname
        self._owns_socket: bool = owns_socket

    @classmethod
    @abc.abstractmethod
    def _create_socket(cls, raw_sock: socket.socket) -> RpcSocketT:
        raise NotImplementedError

    @zyncio.zclassmethod
    @classmethod
    async def connect(cls, raw_sock: socket.socket, messages: RpcMessageRegistry | None = None) -> Self:
        sock = cls._create_socket(raw_sock)
        handshake = await sock.rpc_handshake_recv.z()
        if handshake.server_version != ProtocolConstants.SERVER_VERSION:
            raise InvalidServerVersionMagicError(
                f"got {handshake.magic:x} instead of {ProtocolConstants.SERVER_VERSION:x}"
            )
        return cls(
            sock, handshake.client_id, handshake.platform.lower(), handshake.arch, handshake.sysname.lower(), messages
        )

    async def rpc_call(self, msg_id: int, **kwargs) -> Any:
        """
        Resolve msg_id/reply class from request_msg's type, build RpcMessage, send and, parse reply.
        """
        req = self.messages.get(msg_id)(**kwargs)
        msg = RpcMessage(
            client_id=self.client_id,
            msg_id=msg_id,
            payload=req.SerializeToString(),
        )
        rep_msg = await self.sock.rpc_msg_send_recv.z(msg)
        rep = self.messages.get(rep_msg.msg_id)()
        rep.ParseFromString(rep_msg.payload)
        if rep_msg.msg_id == ProtocolConstants.REP_ERROR:
            logger.error(f"Server error: {rep.message}")
            raise ServerResponseError(rep.message)
        return rep

    def close(self) -> None:
        if not self._owns_socket:
            raise RuntimeError("socket is owned by another client")
        self.sock.raw_socket.close()

    def clone(self) -> Self:
        return type(self)(
            self.sock, self.client_id, self.platform, self.arch, self.sysname, self.messages.clone(), owns_socket=False
        )


class SyncRpcBridge(zyncio.SyncMixin, RpcBridge[SyncRpcSocket]):
    @classmethod
    def _create_socket(cls, raw_sock: socket.socket) -> SyncRpcSocket:
        return SyncRpcSocket(raw_sock)


class AsyncRpcBridge(zyncio.AsyncMixin, RpcBridge[AsyncRpcSocket]):
    @classmethod
    def _create_socket(cls, raw_sock: socket.socket) -> AsyncRpcSocket:
        return AsyncRpcSocket(raw_sock)
