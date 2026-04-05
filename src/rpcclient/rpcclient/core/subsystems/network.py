import socket as pysock
from collections import namedtuple
from typing import TYPE_CHECKING

import zyncio

from rpcclient.clients.darwin.structs import timeval
from rpcclient.core._types import ClientBound, ClientT_co
from rpcclient.core.allocated import Allocated
from rpcclient.core.structs.consts import (
    AF_INET,
    AF_INET6,
    AF_UNIX,
    EPIPE,
    F_GETFL,
    F_SETFL,
    MSG_NOSIGNAL,
    O_NONBLOCK,
    SO_RCVBUF,
    SO_RCVTIMEO,
    SO_SNDBUF,
    SO_SNDTIMEO,
    SOCK_STREAM,
    SOL_SOCKET,
)
from rpcclient.core.structs.generic import (
    parse_hostent,
    parse_ifaddrs,
    sockaddr,
    sockaddr_in,
    sockaddr_in6,
    sockaddr_un,
    uint32_t,
)
from rpcclient.core.symbol import BaseSymbol
from rpcclient.exceptions import BadReturnValueError


if TYPE_CHECKING:
    pass


Interface = namedtuple("Interface", "name address netmask broadcast")
Hostentry = namedtuple("Hostentry", "name aliases addresses")


class Socket(Allocated[ClientT_co]):
    CHUNK_SIZE = 1024

    def __init__(self, client: ClientT_co, fd: int) -> None:
        """
        :param rpcclient.client.client.Client client:
        :param fd:
        """
        super().__init__()
        self._client = client
        self.fd: int = fd
        self._blocking: bool | None
        self._timeout = None

    async def _deallocate(self) -> None:
        """Close the remote socket file descriptor."""
        fd = (await self._client.symbols.close.z(self.fd)).c_int32
        if fd < 0:
            raise BadReturnValueError(f"failed to close fd: {fd}")

    @zyncio.zmethod
    async def send(self, buf: bytes | BaseSymbol, size: int | None = None, flags: int = 0) -> int:
        """
        Send bytes from buf on the remote socket fd.

        :param buf: buffer to send
        :param size: If None, use len(buf)
        :param flags: flags for send() syscall. MSG_NOSIGNAL will always be added
        :return: how many bytes were sent
        """
        if size is None:
            if isinstance(buf, BaseSymbol):
                raise ValueError("cannot calculate size argument for Symbol objects")
            size = len(buf)
        n = (await self._client.symbols.send.z(self.fd, buf, size, MSG_NOSIGNAL | flags)).c_int64
        if n < 0:
            if await self._client.get_errno.z() == EPIPE:
                await self.deallocate.z()
            await self._client.raise_errno_exception.z(f"failed to send on fd: {self.fd}")
        return n

    @zyncio.zmethod
    async def sendall(self, buf: bytes, flags: int = 0) -> None:
        """Send the entire buffer, retrying until all bytes are written."""
        size = len(buf)
        offset = 0
        async with self._client.safe_malloc.z(size) as block:
            await block.poke.z(buf)
            while offset < size:
                sent = await self.send.z(block + offset, size - offset, flags=flags)
                offset += sent

    async def _recv(self, chunk: BaseSymbol, size: int, flags: int = 0) -> bytes:
        err = (await self._client.symbols.recv.z(self.fd, chunk, size, MSG_NOSIGNAL | flags)).c_int64
        if err < 0:
            await self._client.raise_errno_exception.z(f"recv() failed for fd: {self.fd}")
        elif err == 0:
            await self._client.raise_errno_exception.z(f"recv() failed for fd: {self.fd} (peer closed)")
        return await chunk.peek.z(err)

    @zyncio.zmethod
    async def recv(self, size: int = CHUNK_SIZE, flags: int = 0) -> bytes:
        """
        Receive up to size bytes from the remote socket fd.

        :param size: chunk size
        :param flags: flags for recv() syscall. MSG_NOSIGNAL will always be added
        :return: received bytes
        """
        async with self._client.safe_malloc.z(size) as chunk:
            return await self._recv(chunk, size, flags=flags)

    @zyncio.zmethod
    async def recvall(self, size: int, flags: int = 0) -> bytes:
        """recv at remote until all buffer is received"""
        buf = b""
        async with self._client.safe_malloc.z(size) as chunk:
            while len(buf) < size:
                buf += await self._recv(chunk, size - len(buf), flags=flags)
        return buf

    @zyncio.zmethod
    async def setsockopt(self, level: int, option_name: int, option_value: bytes):
        if await self._client.symbols.setsockopt.z(self.fd, level, option_name, option_value, len(option_value)) != 0:
            await self._client.raise_errno_exception.z(f"setsockopt() failed: {await self._client.get_last_error.z()}")

    @zyncio.zmethod
    async def setbufsize(self, size: int) -> None:
        await self.setsockopt.z(SOL_SOCKET, SO_SNDBUF, uint32_t.build(size))
        await self.setsockopt.z(SOL_SOCKET, SO_RCVBUF, uint32_t.build(size))

    @zyncio.zmethod
    async def settimeout(self, seconds: int) -> None:
        self._timeout = seconds
        await self.setsockopt.z(SOL_SOCKET, SO_RCVTIMEO, timeval.build({"tv_sec": seconds, "tv_usec": 0}))
        await self.setsockopt.z(SOL_SOCKET, SO_SNDTIMEO, timeval.build({"tv_sec": seconds, "tv_usec": 0}))

    @zyncio.zmethod
    async def gettimeout(self) -> int | None:
        return self._timeout

    @zyncio.zmethod
    async def setblocking(self, blocking: bool) -> None:
        opts = (await self._client.symbols.fcntl.z(self.fd, F_GETFL, 0)).c_uint64
        if not blocking:
            opts |= O_NONBLOCK
        else:
            opts &= ~O_NONBLOCK
        if await self._client.symbols.fcntl.z(self.fd, F_SETFL, opts) != 0:
            await self._client.raise_errno_exception.z(f"fcntl() failed: {await self._client.get_last_error.z()}")
        self._blocking = blocking

    @zyncio.zmethod
    async def getblocking(self) -> bool:
        if self._blocking is None:
            self._blocking = await self._getblocking()

        return self._blocking

    async def _getblocking(self) -> bool:
        return not bool(await self._client.symbols.fcntl.z(self.fd, F_GETFL, 0) & O_NONBLOCK)

    def __repr__(self) -> str:
        if zyncio.is_sync(self):
            blocking = self.getblocking()
        else:
            blocking = self._blocking if self._blocking is not None else "<unknown>"
        return f"<{self.__class__.__name__} FD:{self.fd} BLOCKING:{blocking}>"


class Network(ClientBound[ClientT_co]):
    def __init__(self, client: ClientT_co) -> None:
        """
        :param rpcclient.client.client.Client client:
        """
        self._client = client

    @zyncio.zmethod
    async def socket(self, family=AF_INET, socktype=SOCK_STREAM, proto=0) -> int:
        """Create a remote socket and return its file descriptor."""
        result = (await self._client.symbols.socket.z(family, socktype, proto)).c_int64
        if result == 0:
            await self._client.raise_errno_exception.z(f"failed to create socket: {result}")
        return result

    @zyncio.zmethod
    async def tcp_connect(self, address: str, port: int) -> Socket:
        """make target connect to given address:port and get socket object"""
        family = AF_INET6 if ":" in address else AF_INET
        sockfd = await self.socket.z(family=family, socktype=SOCK_STREAM, proto=0)
        if family == AF_INET:
            servaddr = sockaddr_in.build({"sin_addr": pysock.inet_pton(family, address), "sin_port": port})
        else:
            servaddr = sockaddr_in6.build({"sin6_addr": pysock.inet_pton(family, address), "sin6_port": port})
        await self._client.set_errno.z(0)
        error = (await self._client.symbols.connect.z(sockfd, servaddr, len(servaddr))).c_int64
        if error == -1:
            await self._client.symbols.close.z(sockfd)
            await self._client.raise_errno_exception.z(f"failed connecting to: {address}:{port}")
        return Socket(self._client, sockfd)

    @zyncio.zmethod
    async def unix_connect(self, filename: str) -> Socket:
        """make target connect to given unix path and get socket object"""
        sockfd = await self.socket.z(family=AF_UNIX, socktype=SOCK_STREAM, proto=0)
        servaddr = sockaddr_un.build({"sun_path": filename})
        await self._client.set_errno.z(0)
        error = (await self._client.symbols.connect.z(sockfd, servaddr, len(servaddr))).c_int64
        if error == -1:
            await self._client.symbols.close.z(sockfd)
            await self._client.raise_errno_exception.z(f"failed connecting to: {filename}")
        return Socket(self._client, sockfd)

    @zyncio.zmethod
    async def gethostbyname(self, name: str) -> Hostentry | None:
        """Query DNS record. Returns None if not found."""
        aliases = []
        addresses = []
        result = await self._client.symbols.gethostbyname.z(name)
        if result == 0:
            return None
        result = await parse_hostent(self._client, result)
        p_aliases = result.h_aliases

        i = 0
        while p_aliases[i]:
            aliases.append(p_aliases[i].peek_str())
            i += 1

        addr_list = result.h_addr_list

        i = 0
        while addr_list[i]:
            addresses.append(pysock.inet_ntoa(addr_list[i].peek(4)))
            i += 1

        return Hostentry(name=result.h_name, aliases=aliases, addresses=addresses)

    @zyncio.zproperty
    async def interfaces(self) -> list[Interface]:
        """get current interfaces"""
        results = []
        async with self._client.safe_calloc.z(8) as addresses:
            if (await self._client.symbols.getifaddrs.z(addresses)).c_int64 < 0:
                await self._client.raise_errno_exception.z("getifaddrs failed")

            current = await parse_ifaddrs(self._client, await addresses.getindex(0))

            while current:
                family = sockaddr.parse(current.ifa_addr.peek(sockaddr.sizeof())).sa_family

                if family == AF_INET:
                    address = pysock.inet_ntoa(sockaddr_in.parse_stream(current.ifa_addr).sin_addr)
                    netmask = pysock.inet_ntoa(sockaddr_in.parse_stream(current.ifa_netmask).sin_addr)
                    broadcast = pysock.inet_ntoa(sockaddr_in.parse_stream(current.ifa_dstaddr).sin_addr)
                    results.append(
                        Interface(name=current.ifa_name, address=address, netmask=netmask, broadcast=broadcast)
                    )

                current = current.ifa_next

            await self._client.symbols.freeifaddrs.z(await addresses.getindex(0))
        return results
