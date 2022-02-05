import socket as pysock
import typing
from collections import namedtuple

from pyzshell.exceptions import ZShellError
from pyzshell.structs.consts import AF_UNIX, AF_INET, SOCK_STREAM
from pyzshell.structs.generic import sockaddr_in, sockaddr_un, ifaddrs, sockaddr

Interface = namedtuple('Interface', 'name address netmask broadcast')


class Socket:
    CHUNK_SIZE = 1024

    def __init__(self, client, fd: int):
        """
        :param pyzshell.client.client.Client client:
        :param fd:
        """
        self._client = client
        self.fd = fd

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """ close(fd) at remote. read man for more details. """
        fd = self._client.symbols.close(self.fd).c_int32
        if fd < 0:
            raise ZShellError(f'failed to close fd: {fd}')

    def send(self, buf: bytes, size: int) -> int:
        """ send(fd, buf, size, 0) at remote. read man for more details. """
        n = self._client.symbols.send(self.fd, buf, size, 0).c_int64
        if n < 0:
            raise ZShellError(f'failed to send on fd: {self.fd}')
        return n

    def sendall(self, buf: bytes):
        """ continue call send() until """
        while buf:
            err = self.send(buf, len(buf))
            buf = buf[err:]

    def recv(self, size: int = CHUNK_SIZE) -> bytes:
        """ recv(fd, buf, size, 0) at remote. read man for more details. """
        with self._client.safe_malloc(size) as chunk:
            err = self._client.symbols.recv(self.fd, chunk, self.CHUNK_SIZE).c_int64
            if err < 0:
                raise ZShellError(f'read failed for fd: {self.fd}')
            return chunk.peek(err)

    def recvall(self, size: int) -> bytes:
        """ recv at remote until all buffer is received """
        buf = b''
        with self._client.safe_malloc(self.CHUNK_SIZE) as chunk:
            while len(buf) < size:
                err = self._client.symbols.read(self.fd, chunk, self.CHUNK_SIZE).c_int64
                if err <= 0:
                    raise ZShellError(f'read failed for fd: {self.fd}')
                buf += chunk.peek(err)
        return buf


class Network:
    def __init__(self, client):
        """
        :param pyzshell.client.client.Client client:
        """
        self._client = client

    def socket(self, family=AF_INET, type=SOCK_STREAM, proto=0) -> int:
        """ socket(family, type, proto) at remote. read man for more details. """
        result = self._client.symbols.socket(family, type, proto).c_int64
        if 0 == result:
            raise ZShellError(f'failed to create socket: {result}')
        return result

    def tcp_connect(self, address: str, port: int) -> Socket:
        """ make target connect to given address:port and get socket object """
        sockfd = self.socket(family=AF_INET, type=SOCK_STREAM, proto=0)
        servaddr = sockaddr_in.build(
            {'sin_addr': pysock.inet_aton(address), 'sin_port': pysock.htons(port)})
        self._client.symbols.errno[0] = 0
        self._client.symbols.connect(sockfd, servaddr, len(servaddr))
        if self._client.errno:
            raise ZShellError(f'failed connecting to: {address}:{port} ({self._client.errno})')
        return Socket(self._client, sockfd)

    def unix_connect(self, filename: str) -> Socket:
        """ make target connect to given unix path and get socket object """
        sockfd = self.socket(family=AF_UNIX, type=SOCK_STREAM, proto=0)
        servaddr = sockaddr_un.build({'sun_path': filename})
        self._client.symbols.errno[0] = 0
        self._client.symbols.connect(sockfd, servaddr, len(servaddr))
        if self._client.errno:
            raise ZShellError(f'failed connecting to: {filename} ({self._client.errno})')
        return Socket(self._client, sockfd)

    @property
    def interfaces(self) -> typing.List[Interface]:
        """ get current interfaces """
        results = []
        my_ifaddrs = ifaddrs(self._client)
        with self._client.safe_calloc(8) as addresses:
            if self._client.symbols.getifaddrs(addresses).c_int64 < 0:
                raise ZShellError('getifaddrs failed')

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
