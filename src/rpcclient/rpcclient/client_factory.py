import logging
import os
import subprocess
import tempfile
import typing
from pathlib import Path
from socket import socket
from zipfile import ZipFile

import requests

from rpcclient.client import Client
from rpcclient.exceptions import FailedToConnectError, InvalidServerVersionMagicError
from rpcclient.ios.client import IosClient
from rpcclient.linux.client import LinuxClient
from rpcclient.macos.client import MacosClient
from rpcclient.protocol import DEFAULT_PORT, SERVER_MAGIC_VERSION, protocol_handshake_t

PROJECT_URL = 'https://github.com/doronz88/rpc-project/archive/refs/heads/master.zip'
RPCSERVER_SUBDIR = 'rpc-project-master/src/rpcserver'
HOMEDIR = Path('~/.rpc-project').expanduser()

logger = logging.getLogger(__name__)


def recvall(sock, size: int) -> bytes:
    buf = b''
    while size:
        chunk = sock.recv(size)
        if not chunk:
            raise FailedToConnectError()
        size -= len(chunk)
        buf += chunk
    return buf


def create_local() -> typing.Union[Client, IosClient, MacosClient, LinuxClient]:
    if not HOMEDIR.exists():
        with tempfile.TemporaryDirectory() as temp_dir:
            local_zip = Path(temp_dir) / 'master.zip'
            local_zip.write_bytes(requests.get(PROJECT_URL).content)
            ZipFile(local_zip).extractall(HOMEDIR)
    os.chdir(HOMEDIR / RPCSERVER_SUBDIR)
    cwd = os.getcwd()

    assert 0 == os.system('make')

    server = socket()
    server.bind(('127.0.0.1', 0))
    available_port = server.getsockname()[1]
    server.close()

    proc = subprocess.Popen(['./rpcserver', '-p', str(available_port)], cwd=cwd)
    logger.info(f'server launched at pid {proc.pid}')

    while True:
        try:
            return create_tcp_client('127.0.0.1', available_port)
        except FailedToConnectError:
            pass


def create_tcp_client(hostname: str, port: int = DEFAULT_PORT) -> \
        typing.Union[Client, IosClient, MacosClient, LinuxClient]:
    def tcp_connect() -> socket:
        sock = socket()
        try:
            sock.connect((hostname, port))
        except ConnectionRefusedError as e:
            # wrap in our own exception
            raise FailedToConnectError() from e
        return sock

    return create_client(tcp_connect)


def create_client(create_socket_cb: typing.Callable) -> typing.Union[Client, IosClient, MacosClient, LinuxClient]:
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
