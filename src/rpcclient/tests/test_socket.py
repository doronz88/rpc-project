import contextlib
import socket
import time
from multiprocessing import Event, Process

import pytest

from rpcclient.exceptions import RpcConnectionRefusedError, RpcFileNotFoundError, RpcResourceTemporarilyUnavailableError

RAND_PORT = 8989
BAD_SOCK = '/tmp/BAD'
TIMEOUT = 10
CHUNK_SIZE = 1024


def recvall(sock, size: int) -> bytes:
    buf = b''
    while len(buf) < size:
        buf += sock.recv(size - len(buf))
    return buf


def server_process_handler(server, event):
    event.set()
    client = server.accept()[0]
    while True:
        received = client.recv(CHUNK_SIZE)
        client.sendall(received)


@contextlib.contextmanager
def tcp_server():
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    port = server.getsockname()[1]
    server.listen(1)
    event = Event()
    server_process = Process(target=server_process_handler, args=(server, event,))
    server_process.start()
    event.wait()
    try:
        yield port
    finally:
        server_process.kill()


@contextlib.contextmanager
def unix_server(tmp_path):
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock_path = tmp_path / 'sock'
    sock_path = str(sock_path.absolute())
    server.bind(sock_path)
    server.listen(1)
    event = Event()
    server_process = Process(target=server_process_handler, args=(server, event,))
    server_process.start()
    event.wait()
    try:
        yield sock_path
    finally:
        server_process.kill()


def test_tcp_connection_refused(client):
    with pytest.raises(RpcConnectionRefusedError):
        with client.network.tcp_connect('127.0.0.1', RAND_PORT):
            pass


def test_unix_connection_refused(client):
    with pytest.raises(RpcFileNotFoundError):
        with client.network.unix_connect(BAD_SOCK):
            pass


@pytest.mark.local_machine
@pytest.mark.parametrize('send_buf', [
    b'a',
    b'b' * 20,
    b'c' * 1024,
])
def test_tcp_send_receive(client, send_buf: bytes):
    with tcp_server() as port:
        with client.network.tcp_connect('127.0.0.1', port) as sock:
            sock.sendall(send_buf)
            assert recvall(sock, len(send_buf)) == send_buf


@pytest.mark.local_machine
@pytest.mark.parametrize('send_buf', [
    b'a',
    b'b' * 20,
    b'c' * 1024,
])
def test_unix_send_receive(client, tmp_path, send_buf: bytes):
    with unix_server(tmp_path) as sock_path:
        with client.network.unix_connect(sock_path) as sock:
            sock.sendall(send_buf)
            assert recvall(sock, len(send_buf)) == send_buf


@pytest.mark.local_machine
def test_tcp_receive_timeout(client):
    with tcp_server() as port:
        with client.network.tcp_connect('127.0.0.1', port) as sock:
            sock.settimeout(TIMEOUT)
            start = time.time()
            with pytest.raises(RpcResourceTemporarilyUnavailableError):
                sock.recv(1)
    assert time.time() - start >= TIMEOUT


@pytest.mark.local_machine
def test_unix_receive_timeout(client, tmp_path):
    with unix_server(tmp_path) as tmp_sock:
        with client.network.unix_connect(tmp_sock) as sock:
            sock.settimeout(TIMEOUT)
            start = time.time()
            with pytest.raises(RpcResourceTemporarilyUnavailableError):
                sock.recv(1)
        assert time.time() - start >= TIMEOUT
