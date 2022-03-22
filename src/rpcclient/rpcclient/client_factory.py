import logging
from socket import socket

from rpcclient.client import Client
from rpcclient.darwin.client import DarwinClient
from rpcclient.exceptions import FailedToConnectError, InvalidServerVersionMagicError
from rpcclient.ios.client import IosClient
from rpcclient.linux.client import LinuxClient
from rpcclient.macos.client import MacosClient
from rpcclient.protocol import DEFAULT_PORT, SERVER_MAGIC_VERSION, protocol_handshake_t


def recvall(sock, size: int) -> bytes:
    buf = b''
    while size:
        chunk = sock.recv(size)
        if not chunk:
            raise FailedToConnectError()
        size -= len(chunk)
        buf += chunk
    return buf


def create_client(hostname: str, port: int = DEFAULT_PORT):
    sock = socket()
    try:
        sock.connect((hostname, port))
    except ConnectionRefusedError as e:
        # wrap in our own exception
        raise FailedToConnectError() from e

    handshake = protocol_handshake_t.parse(recvall(sock, protocol_handshake_t.sizeof()))

    if handshake.magic != SERVER_MAGIC_VERSION:
        raise InvalidServerVersionMagicError()

    sysname = handshake.sysname.lower()
    arch = handshake.arch

    logging.info(f'connection uname.sysname: {handshake.sysname}')

    if sysname == 'darwin':
        client = DarwinClient(sock, sysname, arch, hostname, port)

        if client.uname.machine.startswith('iPhone'):
            return IosClient(sock, sysname, arch, hostname, port)
        else:
            return MacosClient(sock, sysname, arch, hostname, port)
    elif sysname == 'linux':
        return LinuxClient(sock, sysname, arch, hostname, port)

    return Client(sock, sysname, arch, hostname, port)
