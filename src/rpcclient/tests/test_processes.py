from pathlib import Path
from uuid import uuid4

import pytest

from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.clients.darwin.subsystems.processes import SharedMemoryFd
from rpcclient.clients.ios.client import IosClient
from rpcclient.core.structs.consts import O_CREAT, O_RDWR
from rpcclient.exceptions import LaunchError
from rpcclient.transports import DEFAULT_PORT


LAUNCHD_PID = 1
LAUNCHD_PATH = "/sbin/launchd"


@pytest.mark.darwin
def test_list_sanity(client: DarwinClient) -> None:
    processes = client.processes.list()
    assert len(processes) > 2  # at least launchd and us should be running
    for p in processes:
        if p.pid == LAUNCHD_PID:
            assert p.path == LAUNCHD_PATH


@pytest.mark.darwin
def test_get_process_by_listening_port(client: DarwinClient) -> None:
    # there should only be one process listening on this port and that's us
    worker_process = client.processes.get_by_pid(client.pid)
    assert client.processes.get_processes_by_listening_port(DEFAULT_PORT)[0].pid == worker_process.ppid


@pytest.mark.darwin
def test_process_object(client: DarwinClient) -> None:
    server = client.processes.get_self()
    assert server.pid > 0
    assert len(server.images) > 0
    assert server.path is not None
    assert len([img for img in server.images if Path(img.path).name == Path(server.path).name]) > 0
    fds = server.fds
    assert fds[0].fd == 0
    assert fds[1].fd == 1
    assert fds[2].fd == 2


@pytest.mark.darwin
def test_process_object_includes_shared_memory_fd(client: DarwinClient) -> None:
    shm_name = f"/rpc-{uuid4().hex[:8]}"
    fd = client.symbols.shm_open(shm_name, O_RDWR | O_CREAT, 0o600).c_int32
    if fd < 0:
        client.raise_errno_exception(f"shm_open({shm_name}) failed")

    try:
        shm_fds = [item for item in client.processes.get_self().fds if isinstance(item, SharedMemoryFd)]
        assert any(item.fd == fd and item.path == shm_name for item in shm_fds)
    finally:
        if client.symbols.close(fd) != 0:
            client.raise_errno_exception(f"close({fd}) failed")
        if client.symbols.shm_unlink(shm_name) != 0:
            client.raise_errno_exception(f"shm_unlink({shm_name}) failed")


@pytest.mark.darwin
def test_get_memgraph_snapshot(client: DarwinClient) -> None:
    assert len(client.processes.get_self().parent.get_memgraph_snapshot()) > 0


@pytest.mark.ios
def test_launch_process(client: IosClient) -> None:
    client.processes.launch("com.apple.calculator").kill()


@pytest.mark.ios
def test_launch_invalid_process(client: IosClient) -> None:
    with pytest.raises(LaunchError):
        client.processes.launch("com.apple.cyber")
