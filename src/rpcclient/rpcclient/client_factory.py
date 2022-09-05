import logging
import typing
from socket import socket

from rpcclient.client import Client
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


def create_tcp_client(hostname: str, port: int = DEFAULT_PORT):
    def tcp_connect() -> socket:
        sock = socket()
        try:
            sock.connect((hostname, port))
        except ConnectionRefusedError as e:
            # wrap in our own exception
            raise FailedToConnectError() from e
        return sock

    return create_client(tcp_connect)


def create_client(create_socket_cb: typing.Callable):
    sock = create_socket_cb()
    handshake = protocol_handshake_t.parse(recvall(sock, protocol_handshake_t.sizeof()))

    if handshake.magic != SERVER_MAGIC_VERSION:
        raise InvalidServerVersionMagicError(f'got {handshake.magic:x} instead of {SERVER_MAGIC_VERSION:x}')

    sysname = handshake.sysname.lower()
    machine = handshake.machine.lower()
    arch = handshake.arch

    logging.info(f'connection uname.sysname: {sysname} uname.machine: {machine}')

    if sysname == 'darwin':
        if machine.startswith('iphone'):
            return IosClient(sock, sysname, arch, create_socket_cb)
        else:
            return MacosClient(sock, sysname, arch, create_socket_cb)
    elif sysname == 'linux':
        return LinuxClient(sock, sysname, arch, create_socket_cb)

    return Client(sock, sysname, arch, create_socket_cb)
