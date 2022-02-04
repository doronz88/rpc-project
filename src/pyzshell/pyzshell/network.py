import socket as pysock

from pyzshell.exceptions import ZShellError
from pyzshell.structs.generic import sockaddr_in


class Network:
    def __init__(self, client):
        self._client = client

    def socket(self, family=pysock.AF_INET, type=pysock.SOCK_STREAM, proto=0) -> int:
        result = self._client.symbols.socket(family, type, proto).c_int64
        if 0 == result:
            raise ZShellError(f'failed to create socket: {result}')
        return result

    def tcp_connect(self, address: str, port: int):
        sockfd = self.socket(family=pysock.AF_INET, type=pysock.SOCK_STREAM, proto=0)
        servaddr = sockaddr_in.build(
            {'sin_addr': pysock.inet_aton(address), 'sin_port': pysock.htons(port)})
        self._client.symbols.errno[0] = 0
        self._client.symbols.connect(sockfd, servaddr, len(servaddr))
        if self._client.errno:
            raise ZShellError(f'failed connecting to: {address}:{port} ({self._client.errno})')
        return sockfd
