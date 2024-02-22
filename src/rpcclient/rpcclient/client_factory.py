import logging
import os
import subprocess
import typing
import urllib.request
from socket import socket

import requests

from rpcclient.client import Client
from rpcclient.exceptions import FailedToConnectError
from rpcclient.ios.client import IosClient
from rpcclient.linux.client import LinuxClient
from rpcclient.macos.client import MacosClient
from rpcclient.protosocket import ProtoSocket

PROJECT_URL = 'https://api.github.com/repos/doronz88/rpc-project/releases/latest'
BINARY_NAME = 'rpcserver_macosx'

logger = logging.getLogger(__name__)

DEFAULT_PORT = 5910


def create_local() -> typing.Union[Client, IosClient, MacosClient, LinuxClient]:
    response = requests.get(PROJECT_URL)
    response.raise_for_status()
    data = response.json()
    for asset in data['assets']:
        if asset['name'] == BINARY_NAME:
            download_url = asset['browser_download_url']
            logger.info(f'Downloading {BINARY_NAME} from {download_url}')
            urllib.request.urlretrieve(download_url, BINARY_NAME)
            logger.info(f'Download completed: {BINARY_NAME}')
            os.chmod(BINARY_NAME, os.stat(BINARY_NAME).st_mode | 0o100)

    server = socket()
    server.bind(('127.0.0.1', 0))
    available_port = server.getsockname()[1]
    server.close()

    proc = subprocess.Popen([f'./{BINARY_NAME}', '-p', str(available_port)], cwd=os.getcwd())
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
    proto_sock = ProtoSocket(sock)

    sysname = proto_sock.handshake.sysname.lower()
    machine = proto_sock.handshake.machine.lower()
    arch = proto_sock.handshake.arch

    logging.info(f'connection uname.sysname: {sysname} uname.machine: {machine}')

    if sysname == 'darwin':
        if machine.startswith('iphone'):
            return IosClient(proto_sock, sysname, arch, create_socket_cb)
        else:
            return MacosClient(proto_sock, sysname, arch, create_socket_cb)
    elif sysname == 'linux':
        return LinuxClient(proto_sock, sysname, arch, create_socket_cb)

    return Client(proto_sock, sysname, arch, create_socket_cb)
