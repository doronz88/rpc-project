import socket as pysock
import typing
from collections import namedtuple

from rpcclient.allocated import Allocated
from rpcclient.darwin.structs import timeval
from rpcclient.exceptions import BadReturnValueError
from rpcclient.structs.consts import AF_UNIX, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_RCVTIMEO, SO_SNDTIMEO, MSG_NOSIGNAL, \
    EPIPE, F_GETFL, O_NONBLOCK, F_SETFL, MSG_DONTWAIT
from rpcclient.structs.generic import sockaddr_in, sockaddr_un, ifaddrs, sockaddr, hostent

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

    def _deallocate(self):
        """ close(fd) at remote. read man for more details. """
        fd = self._client.symbols.close(self.fd).c_int32
        if fd < 0:
            raise BadReturnValueError(f'failed to close fd: {fd}')

    def send(self, buf: bytes, size: int = None) -> int:
        """
        send(fd, buf, size, 0) at remote. read man for more details.

        :param buf: buffer to send
        :param size: If None, use len(buf)
        :return: how many bytes were sent
        """
        if size is None:
            size = len(buf)
        n = self._client.symbols.send(self.fd, buf, size, MSG_NOSIGNAL | MSG_DONTWAIT).c_int64
        if n < 0:
            if self._client.errno == EPIPE:
                self.deallocate()
            raise BadReturnValueError(f'failed to send on fd: {self.fd} ({self._client.last_error})')
        return n

    def sendall(self, buf: bytes):
        """ continue call send() until """
        while buf:
            err = self.send(buf, len(buf))
            buf = buf[err:]

    def _recv(self, chunk, size: int):
        err = self._client.symbols.recv(self.fd, chunk, size, MSG_DONTWAIT).c_int64
        if err < 0:
            raise BadReturnValueError(f'recv() failed for fd: {self.fd} ({self._client.last_error})')
        elif err == 0:
            raise BadReturnValueError(f'recv() failed for fd: {self.fd} (peer closed)')
        return chunk.peek(size)

    def recv(self, size: int = CHUNK_SIZE) -> bytes:
        """
        recv() at remote. read man for more details.

        :param size: chunk size
        :return: received bytes
        """
        with self._client.safe_malloc(size) as chunk:
            return self._recv(chunk, size)

    def recvall(self, size: int) -> bytes:
        """ recv at remote until all buffer is received """
        buf = b''
        with self._client.safe_malloc(size) as chunk:
            while len(buf) < size:
                buf += self._recv(chunk, size)
        return buf

    def setsockopt(self, level: int, option_name: int, option_value: bytes):
        if 0 != self._client.symbols.setsockopt(self.fd, level, option_name, option_value, len(option_value)):
            raise BadReturnValueError(f'setsockopt() failed: {self._client.last_error}')

    def settimeout(self, seconds: int):
        self.setsockopt(SOL_SOCKET, SO_RCVTIMEO, timeval.build({'tv_sec': seconds, 'tv_usec': 0}))
        self.setsockopt(SOL_SOCKET, SO_SNDTIMEO, timeval.build({'tv_sec': seconds, 'tv_usec': 0}))

    def setblocking(self, blocking: bool):
        opts = self._client.symbols.fcntl(self.fd, F_GETFL, 0).c_uint64
        if not blocking:
            opts |= O_NONBLOCK
        else:
            opts &= ~O_NONBLOCK
        if 0 != self._client.symbols.fcntl(self.fd, F_SETFL, opts):
            raise BadReturnValueError(f'fcntl() failed: {self._client.last_error}')
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
            raise BadReturnValueError(f'failed to create socket: {result} ({self._client.last_error})')
        return result

    def tcp_connect(self, address: str, port: int) -> Socket:
        """ make target connect to given address:port and get socket object """
        sockfd = self.socket(family=AF_INET, type=SOCK_STREAM, proto=0)
        servaddr = sockaddr_in.build(
            {'sin_addr': pysock.inet_aton(address), 'sin_port': pysock.htons(port)})
        self._client.errno = 0
        error = self._client.symbols.connect(sockfd, servaddr, len(servaddr))
        if error == -1:
            raise BadReturnValueError(f'failed connecting to: {address}:{port} ({self._client.last_error})')
        return Socket(self._client, sockfd)

    def unix_connect(self, filename: str) -> Socket:
        """ make target connect to given unix path and get socket object """
        sockfd = self.socket(family=AF_UNIX, type=SOCK_STREAM, proto=0)
        servaddr = sockaddr_un.build({'sun_path': filename})
        self._client.errno = 0
        error = self._client.symbols.connect(sockfd, servaddr, len(servaddr))
        if error == -1:
            raise BadReturnValueError(f'failed connecting to: {filename} ({self._client.last_error})')
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
                raise BadReturnValueError('getifaddrs failed')

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
