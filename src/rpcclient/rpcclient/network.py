import socket as pysock
import typing
from collections import namedtuple

from rpcclient.allocated import Allocated
from rpcclient.darwin.structs import timeval
from rpcclient.exceptions import BadReturnValueError
from rpcclient.structs.consts import AF_INET, AF_INET6, AF_UNIX, EPIPE, F_GETFL, F_SETFL, MSG_NOSIGNAL, O_NONBLOCK, \
    SO_RCVTIMEO, SO_SNDTIMEO, SOCK_STREAM, SOL_SOCKET
from rpcclient.structs.generic import hostent, ifaddrs, sockaddr, sockaddr_in, sockaddr_in6, sockaddr_un
from rpcclient.symbol import Symbol

Interface = namedtuple('Interface', 'name address netmask broadcast')
Hostentry = namedtuple('Hostentry', 'name aliases addresses')


class Socket(Allocated):
    CHUNK_SIZE = 1024

    def __init__(self, client, fd: int):
        """
        :param rpcclient.client.client.Client client:
        :param fd:
        """
        super().__init__()
        self._client = client
        self.fd = fd
        self._blocking = self._getblocking()
        self._timeout = None

    def _deallocate(self):
        """ close(fd) at remote. read man for more details. """
        fd = self._client.symbols.close(self.fd).c_int32
        if fd < 0:
            raise BadReturnValueError(f'failed to close fd: {fd}')

    def send(self, buf: typing.Union[bytes, Symbol], size: int = None, flags: int = 0) -> int:
        """
        send(fd, buf, size, 0) at remote. read man for more details.

        :param buf: buffer to send
        :param size: If None, use len(buf)
        :param flags: flags for send() syscall. MSG_NOSIGNAL will always be added
        :return: how many bytes were sent
        """
        if size is None:
            if isinstance(buf, Symbol):
                raise ValueError('cannot calculate size argument for Symbol objects')
            size = len(buf)
        n = self._client.symbols.send(self.fd, buf, size, MSG_NOSIGNAL | flags).c_int64
        if n < 0:
            if self._client.errno == EPIPE:
                self.deallocate()
            self._client.raise_errno_exception(f'failed to send on fd: {self.fd}')
        return n

    def sendall(self, buf: bytes, flags: int = 0) -> None:
        """ continue call send() until """
        size = len(buf)
        offset = 0
        with self._client.safe_malloc(size) as block:
            block.poke(buf)
            while offset < size:
                sent = self.send(block + offset, size - offset, flags=flags)
                offset += sent

    def _recv(self, chunk: Symbol, size: int, flags: int = 0) -> bytes:
        err = self._client.symbols.recv(self.fd, chunk, size, MSG_NOSIGNAL | flags).c_int64
        if err < 0:
            self._client.raise_errno_exception(f'recv() failed for fd: {self.fd}')
        elif err == 0:
            self._client.raise_errno_exception(f'recv() failed for fd: {self.fd} (peer closed)')
        return chunk.peek(err)

    def recv(self, size: int = CHUNK_SIZE, flags: int = 0) -> bytes:
        """
        recv() at remote. read man for more details.

        :param size: chunk size
        :param flags: flags for recv() syscall. MSG_NOSIGNAL will always be added
        :return: received bytes
        """
        with self._client.safe_malloc(size) as chunk:
            return self._recv(chunk, size, flags=flags)

    def recvall(self, size: int, flags: int = 0) -> bytes:
        """ recv at remote until all buffer is received """
        buf = b''
        with self._client.safe_malloc(size) as chunk:
            while len(buf) < size:
                buf += self._recv(chunk, size - len(buf), flags=flags)
        return buf

    def setsockopt(self, level: int, option_name: int, option_value: bytes):
        if 0 != self._client.symbols.setsockopt(self.fd, level, option_name, option_value, len(option_value)):
            self._client.raise_errno_exception(f'setsockopt() failed: {self._client.last_error}')

    def settimeout(self, seconds: int):
        self._timeout = seconds
        self.setsockopt(SOL_SOCKET, SO_RCVTIMEO, timeval.build({'tv_sec': seconds, 'tv_usec': 0}))
        self.setsockopt(SOL_SOCKET, SO_SNDTIMEO, timeval.build({'tv_sec': seconds, 'tv_usec': 0}))

    def gettimeout(self) -> typing.Optional[int]:
        return self._timeout

    def setblocking(self, blocking: bool):
        opts = self._client.symbols.fcntl(self.fd, F_GETFL, 0).c_uint64
        if not blocking:
            opts |= O_NONBLOCK
        else:
            opts &= ~O_NONBLOCK
        if 0 != self._client.symbols.fcntl(self.fd, F_SETFL, opts):
            self._client.raise_errno_exception(f'fcntl() failed: {self._client.last_error}')
        self._blocking = blocking

    def getblocking(self) -> bool:
        return self._blocking

    def _getblocking(self) -> bool:
        return not bool(self._client.symbols.fcntl(self.fd, F_GETFL, 0) & O_NONBLOCK)

    def __repr__(self):
        return f'<{self.__class__.__name__} FD:{self.fd} BLOCKING:{self._blocking}>'


class Network:
    def __init__(self, client):
        """
        :param rpcclient.client.client.Client client:
        """
        self._client = client

    def socket(self, family=AF_INET, type=SOCK_STREAM, proto=0) -> int:
        """ socket(family, type, proto) at remote. read man for more details. """
        result = self._client.symbols.socket(family, type, proto).c_int64
        if 0 == result:
            self._client.raise_errno_exception(f'failed to create socket: {result}')
        return result

    def tcp_connect(self, address: str, port: int) -> Socket:
        """ make target connect to given address:port and get socket object """
        family = AF_INET6 if ':' in address else AF_INET
        sockfd = self.socket(family=family, type=SOCK_STREAM, proto=0)
        if family == AF_INET:
            servaddr = sockaddr_in.build(
                {'sin_addr': pysock.inet_pton(family, address), 'sin_port': port})
        else:
            servaddr = sockaddr_in6.build(
                {'sin6_addr': pysock.inet_pton(family, address), 'sin6_port': port})
        self._client.errno = 0
        error = self._client.symbols.connect(sockfd, servaddr, len(servaddr)).c_int64
        if error == -1:
            self._client.symbols.close(sockfd)
            self._client.raise_errno_exception(f'failed connecting to: {address}:{port}')
        return Socket(self._client, sockfd)

    def unix_connect(self, filename: str) -> Socket:
        """ make target connect to given unix path and get socket object """
        sockfd = self.socket(family=AF_UNIX, type=SOCK_STREAM, proto=0)
        servaddr = sockaddr_un.build({'sun_path': filename})
        self._client.errno = 0
        error = self._client.symbols.connect(sockfd, servaddr, len(servaddr)).c_int64
        if error == -1:
            self._client.symbols.close(sockfd)
            self._client.raise_errno_exception(f'failed connecting to: {filename}')
        return Socket(self._client, sockfd)

    def gethostbyname(self, name: str) -> Hostentry:
        aliases = []
        addresses = []

        result = hostent(self._client).parse_stream(self._client.symbols.gethostbyname(name))
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

    @property
    def interfaces(self) -> typing.List[Interface]:
        """ get current interfaces """
        results = []
        my_ifaddrs = ifaddrs(self._client)
        with self._client.safe_calloc(8) as addresses:
            if self._client.symbols.getifaddrs(addresses).c_int64 < 0:
                self._client.raise_errno_exception('getifaddrs failed')

            current = my_ifaddrs.parse_stream(addresses[0])

            while current:
                family = sockaddr.parse(current.ifa_addr.peek(sockaddr.sizeof())).sa_family

                if family == AF_INET:
                    address = pysock.inet_ntoa(sockaddr_in.parse_stream(current.ifa_addr).sin_addr)
                    netmask = pysock.inet_ntoa(sockaddr_in.parse_stream(current.ifa_netmask).sin_addr)
                    broadcast = pysock.inet_ntoa(sockaddr_in.parse_stream(current.ifa_dstaddr).sin_addr)
                    results.append(
                        Interface(name=current.ifa_name, address=address, netmask=netmask, broadcast=broadcast))

                current = current.ifa_next

            self._client.symbols.freeifaddrs(addresses[0])
        return results
