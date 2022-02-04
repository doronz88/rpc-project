import socket as pysock

from pyzshell.exceptions import ZShellError
from pyzshell.structs.generic import sockaddr_in, sockaddr_un
from pyzshell.structs.consts import AF_UNIX, AF_INET, SOCK_STREAM

CHUNK_SIZE = 1024


class Network:
    def __init__(self, client):
        self._client = client

    def socket(self, family=AF_INET, type=SOCK_STREAM, proto=0) -> int:
        """ socket(family, type, proto) at remote. read man for more details. """
        result = self._client.symbols.socket(family, type, proto).c_int64
        if 0 == result:
            raise ZShellError(f'failed to create socket: {result}')
        return result

    def tcp_connect(self, address: str, port: int) -> int:
        """ make target connect to given address:port and get connection fd """
        sockfd = self.socket(family=AF_INET, type=SOCK_STREAM, proto=0)
        servaddr = sockaddr_in.build(
            {'sin_addr': pysock.inet_aton(address), 'sin_port': pysock.htons(port)})
        self._client.symbols.errno[0] = 0
        self._client.symbols.connect(sockfd, servaddr, len(servaddr))
        if self._client.errno:
            raise ZShellError(f'failed connecting to: {address}:{port} ({self._client.errno})')
        return sockfd

    def unix_connect(self, filename: str) -> int:
        """ make target connect to given unix path and get connection fd """
        sockfd = self.socket(family=AF_UNIX, type=SOCK_STREAM, proto=0)
        servaddr = sockaddr_un.build({'sun_path': filename})
        self._client.symbols.errno[0] = 0
        self._client.symbols.connect(sockfd, servaddr, len(servaddr))
        if self._client.errno:
            raise ZShellError(f'failed connecting to: {filename} ({self._client.errno})')
        return sockfd

    def send(self, fd: int, buf: bytes, size: int, flags: int = 0) -> int:
        """ send(fd, buf, size, flags) at remote. read man for more details. """
        n = self._client.symbols.send(fd, buf, size, flags).c_int64
        if n < 0:
            raise ZShellError(f'failed to write on fd: {fd}')
        return n

    def sendall(self, sockfd: int, buf: bytes):
        """ call send(sockfd, buf) till all buffer is sent """
        while buf:
            err = self.send(sockfd, buf, len(buf), 0)
            buf = buf[err:]

    def recv(self, sockfd: int, size: int = CHUNK_SIZE, flags: int = 0) -> bytes:
        """ recv(fd, buf, size, flags) at remote. read man for more details. """
        with self._client.safe_malloc(size) as buf:
            n = self._client.symbols.recv(sockfd, buf, size, flags).c_int64
            if n < 0:
                raise ZShellError(f'failed to write on fd: {sockfd}')
            return buf
