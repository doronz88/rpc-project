from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin.structs import POLLIN, pollfd
from rpcclient.core.allocated import Allocated
from rpcclient.core.structs.consts import AF_UNIX, SOCK_STREAM
from rpcclient.core.subsystems.network import Socket
from rpcclient.core.symbol import SymbolT_co


if TYPE_CHECKING:
    from rpcclient.core.client import CoreClient

FD_SIZE = 4
READ_SIZE = 0x10000


class CaptureFD(Allocated["CoreClient[SymbolT_co]"], Generic[SymbolT_co]):
    """
    Context manager, capturing output to a given `fd`. Read from it using the `read()` method.
    """

    def __init__(self, client: "CoreClient[SymbolT_co]", fd: int, sock_buf_size: int | None = None) -> None:
        """
        sock_buf_size is required for captures above 6KB, as any write above this value would block until a read is performed.

        :param rpcclient.client.client.Client client: Current client
        :param fd: FD to capture
        :param sock_buf_size: Buffer size for the capture socket, if not specified, default value is used.
        """
        self._client = client
        self.fd: int = fd
        self._backupfd: int | None = None
        self._socket_pair: tuple[int, int] | None = None
        self._sock_buf_size: int | None = sock_buf_size

    async def _allocate(self) -> None:
        async with self._client.safe_malloc(FD_SIZE * 2) as socket_pair:
            socket_pair.item_size = FD_SIZE
            if await self._client.symbols.socketpair(AF_UNIX, SOCK_STREAM, 0, socket_pair) != 0:
                await self._client.raise_errno_exception("socketpair failed")
            self._socket_pair = ((await socket_pair.getindex(0)).c_int32, (await socket_pair.getindex(1)).c_int32)
        if self._sock_buf_size is not None:
            await Socket(self._client, self._socket_pair[0]).setbufsize(self._sock_buf_size)
        self._backupfd = (await self._client.symbols.dup(self.fd)).c_int32
        if self._backupfd == -1:
            self._backupfd = None
            await self._client.raise_errno_exception("dup fd failed")
        if await self._client.symbols.dup2(self._socket_pair[0], self.fd) < 0:
            await self._client.raise_errno_exception("dup2 sock-fd failed")

    async def _deallocate(self) -> None:
        if self._backupfd is not None:
            if await self._client.symbols.dup2(self._backupfd, self.fd) < 0:
                await self._client.raise_errno_exception("dup2 backup-fd failed")
            if await self._client.symbols.close(self._backupfd) != 0:
                await self._client.raise_errno_exception("close backupfd failed")
            self._backupfd = None
        if self._socket_pair is not None:
            if await self._client.symbols.close(self._socket_pair[0]) != 0:
                await self._client.raise_errno_exception(f"close _socket_pair[0] {self._socket_pair[0]} failed")
            if await self._client.symbols.close(self._socket_pair[1]) != 0:
                await self._client.raise_errno_exception(f"close _socket_pair[1] {self._socket_pair[1]} failed")
            self._socket_pair = None

    async def read(self) -> bytes:
        """Read the bytes captured from `fd` so far."""
        data = b""
        if self._socket_pair is not None:
            async with self._client.safe_malloc(READ_SIZE) as buff:
                read = READ_SIZE
                while read == READ_SIZE:
                    async with self._client.safe_malloc(pollfd.sizeof()) as pfds:
                        await pfds.poke(pollfd.build({"fd": self._socket_pair[1], "events": POLLIN, "revents": 0}))
                        if await self._client.symbols.poll(pfds, 1, 0) != 1:
                            return data
                    read = (await self._client.symbols.read(self._socket_pair[1], buff, READ_SIZE)).c_int32
                    if read == -1:
                        await self._client.raise_errno_exception("read fd failed")
                    data += await buff.peek(read)
        return data
