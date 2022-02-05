import logging
from socket import socket

from pyzshell.client.client import Client
from pyzshell.client.darwin_client import DarwinClient
from pyzshell.client.linux_client import LinuxClient
from pyzshell.protocol import UNAME_VERSION_LEN, DEFAULT_PORT


def recvall(sock, size: int) -> bytes:
    buf = b''
    while size:
        try:
            chunk = sock.recv(size)
        except BlockingIOError:
            continue
        size -= len(chunk)
        buf += chunk
    return buf


def create_client(hostname: str, port: int = DEFAULT_PORT):
    sock = socket()
    sock.connect((hostname, port))
    uname_version = recvall(sock, UNAME_VERSION_LEN).split(b'\x00', 1)[0].decode()
    logging.info(f'connected system uname.version: {uname_version}')
    os_flavor = uname_version.split()[0].lower()

    if os_flavor == 'darwin':
        return DarwinClient(sock, uname_version, hostname, port)
    elif 'Ubuntu' in uname_version:
        return LinuxClient(sock, uname_version, hostname, port)

    return Client(sock, uname_version, hostname, port)
