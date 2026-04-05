import abc
import asyncio
import logging
import socket
import struct
import threading
from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import zyncio

from rpcclient.exceptions import ServerDiedError
from rpcclient.protos.rpc_pb2 import Handshake, ProtocolConstants, RpcMessage, RpcPtyMessage


logger = logging.getLogger(__name__)


SIZE_HEADER_STRUCT = struct.Struct("<Q")


class RpcSocket(zyncio.ZyncBase, abc.ABC):
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

    def __init__(self, sock: socket.socket) -> None:
        self.raw_socket: socket.socket = sock

    @abc.abstractmethod
    def _acquire_protocol_lock(self) -> AbstractAsyncContextManager[None]: ...

    async def _msg_recv(self) -> bytes:
        try:
            (size,) = SIZE_HEADER_STRUCT.unpack(await self._recv(SIZE_HEADER_STRUCT.size))
            buff = await self._recvall(size)
        except struct.error as e:
            raise ConnectionError() from e
        return buff

    async def _msg_send(self, message: bytes) -> None:
        buff = SIZE_HEADER_STRUCT.pack(len(message)) + message
        if self.__zync_mode__ is zyncio.SYNC:
            self.raw_socket.sendall(buff)
        else:
            await asyncio.get_running_loop().sock_sendall(self.raw_socket, buff)

    async def _recv(self, size: int) -> bytes:
        if self.__zync_mode__ is zyncio.SYNC:
            return self.raw_socket.recv(size)
        else:
            return await asyncio.get_running_loop().sock_recv(self.raw_socket, size)

    async def _recvall(self, size: int) -> bytes:
        buf = b""

        while size:
            try:
                chunk = await self._recv(size)
            except BlockingIOError:
                continue
            if not self.raw_socket.getblocking() and not chunk:
                raise ServerDiedError()
            size -= len(chunk)
            buf += chunk
        return buf

    @zyncio.zmethod
    async def rpc_handshake_recv(self) -> Handshake:
        rpc_handshake = Handshake()
        rpc_handshake.ParseFromString(await self._msg_recv())
        return rpc_handshake

    @zyncio.zmethod
    async def rpc_msg_recv(self) -> RpcMessage:
        rpc_msg = RpcMessage()
        rpc_msg.ParseFromString(await self._msg_recv())
        return rpc_msg

    @zyncio.zmethod
    async def rpc_msg_recv_pty(self) -> RpcPtyMessage:
        rpc_msg = RpcPtyMessage()
        rpc_msg.ParseFromString(await self._msg_recv())
        return rpc_msg

    @zyncio.zmethod
    async def rpc_msg_send(self, msg: RpcMessage) -> None:
        msg.magic = ProtocolConstants.MESSAGE_MAGIC
        rpc_msg = msg.SerializeToString()
        await self._msg_send(rpc_msg)

    @zyncio.zmethod
    async def rpc_msg_send_recv(self, msg: RpcMessage) -> RpcMessage:
        async with self._acquire_protocol_lock():
            await self.rpc_msg_send.z(msg)
            return await self.rpc_msg_recv.z()


class SyncRpcSocket(zyncio.SyncMixin, RpcSocket):
    def __init__(self, sock: socket.socket) -> None:
        self._protocol_lock: threading.Lock = threading.Lock()
        super().__init__(sock)

    @asynccontextmanager
    async def _acquire_protocol_lock(self) -> AsyncGenerator[None]:
        with self._protocol_lock:
            yield


class AsyncRpcSocket(zyncio.AsyncMixin, RpcSocket):
    def __init__(self, sock: socket.socket) -> None:
        self._protocol_lock: asyncio.Lock = asyncio.Lock()
        super().__init__(sock)

    @asynccontextmanager
    async def _acquire_protocol_lock(self) -> AsyncGenerator[None]:
        async with self._protocol_lock:
            yield
