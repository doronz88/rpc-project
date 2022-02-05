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
    sysname = recvall(sock, UNAME_VERSION_LEN).split(b'\x00', 1)[0].decode().lower()
    logging.info(f'connection uname.sysname: {sysname}')

    if sysname == 'darwin':
        return DarwinClient(sock, sysname, hostname, port)
    elif sysname == 'linux':
        return LinuxClient(sock, sysname, hostname, port)

    return Client(sock, sysname, hostname, port)
