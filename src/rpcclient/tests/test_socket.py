import contextlib
import multiprocessing
import multiprocessing.synchronize
import socket
import time
from collections.abc import Generator
from multiprocessing import Event, Process
from typing import NoReturn

import pytest

from rpcclient.core.subsystems.fs import RemotePath
from rpcclient.exceptions import RpcConnectionRefusedError, RpcFileNotFoundError, RpcResourceTemporarilyUnavailableError
from tests._types import SyncClient


RAND_PORT = 8989
BAD_SOCK = "/tmp/BAD"
TIMEOUT = 10
CHUNK_SIZE = 1024


def recvall(sock, size: int) -> bytes:
    buf = b""
    while len(buf) < size:
        buf += sock.recv(size - len(buf))
    return buf


def server_process_handler(server: socket.socket, event: multiprocessing.synchronize.Event) -> NoReturn:
    event.set()
    client = server.accept()[0]
    while True:
        received = client.recv(CHUNK_SIZE)
        client.sendall(received)


@contextlib.contextmanager
def tcp_server() -> Generator[int]:
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    port = server.getsockname()[1]
    server.listen(1)
    event = Event()
    server_process = Process(
        target=server_process_handler,
        args=(
            server,
            event,
        ),
    )
    try:
        server_process.start()
        event.wait()
        yield port
    finally:
        server_process.kill()


@contextlib.contextmanager
def unix_server(tmp_path: RemotePath[SyncClient]) -> Generator[str]:
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock_path = tmp_path / "sock"
    sock_path = str(sock_path.absolute())
    server.bind(sock_path)
    server.listen(1)
    event = Event()
    server_process = Process(
        target=server_process_handler,
        args=(
            server,
            event,
        ),
    )
    server_process.start()
    event.wait()
    try:
        yield sock_path
    finally:
        server_process.kill()


def test_tcp_connection_refused(client: SyncClient) -> None:
    with pytest.raises(RpcConnectionRefusedError), client.network.tcp_connect("127.0.0.1", RAND_PORT):
        pass


def test_unix_connection_refused(client: SyncClient) -> None:
    with pytest.raises(RpcFileNotFoundError), client.network.unix_connect(BAD_SOCK):
        pass


@pytest.mark.local_machine
@pytest.mark.parametrize(
    "send_buf",
    [
        b"a",
        b"b" * 20,
        b"c" * 1024,
    ],
)
def test_tcp_send_receive(client: SyncClient, send_buf: bytes) -> None:
    with tcp_server() as port, client.network.tcp_connect("127.0.0.1", port) as sock:
        sock.sendall(send_buf)
        assert recvall(sock, len(send_buf)) == send_buf


@pytest.mark.local_machine
@pytest.mark.parametrize(
    "send_buf",
    [
        b"a",
        b"b" * 20,
        b"c" * 1024,
    ],
)
def test_unix_send_receive(client: SyncClient, tmp_path: RemotePath[SyncClient], send_buf: bytes) -> None:
    with unix_server(tmp_path) as sock_path, client.network.unix_connect(sock_path) as sock:
        sock.sendall(send_buf)
        assert recvall(sock, len(send_buf)) == send_buf


@pytest.mark.local_machine
def test_tcp_receive_timeout(client: SyncClient) -> None:
    with tcp_server() as port, client.network.tcp_connect("127.0.0.1", port) as sock:
        sock.settimeout(TIMEOUT)
        start = time.time()
        with pytest.raises(RpcResourceTemporarilyUnavailableError):
            sock.recv(1)
    assert time.time() - start >= TIMEOUT


@pytest.mark.local_machine
def test_unix_receive_timeout(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    with unix_server(tmp_path) as tmp_sock:
        with client.network.unix_connect(tmp_sock) as sock:
            sock.settimeout(TIMEOUT)
            start = time.time()
            with pytest.raises(RpcResourceTemporarilyUnavailableError):
                sock.recv(1)
        assert time.time() - start >= TIMEOUT
