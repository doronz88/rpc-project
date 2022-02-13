import logging
from socket import socket

from rpcclient.client import Client
from rpcclient.darwin.client import DarwinClient
from rpcclient.linux.client import LinuxClient
from rpcclient.exceptions import FailedToConnectError
from rpcclient.protocol import UNAME_VERSION_LEN, DEFAULT_PORT


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

    sysname = recvall(sock, UNAME_VERSION_LEN).split(b'\x00', 1)[0].decode().lower()
    logging.info(f'connection uname.sysname: {sysname}')

    if sysname == 'darwin':
        return DarwinClient(sock, sysname, hostname, port)
    elif sysname == 'linux':
        return LinuxClient(sock, sysname, hostname, port)

    return Client(sock, sysname, hostname, port)
