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
async def test_list_sanity(client: DarwinClient) -> None:
    processes = await client.processes.list()
    assert len(processes) > 2  # at least launchd and us should be running
    for p in processes:
        if p.pid == LAUNCHD_PID:
            assert await p.path() == LAUNCHD_PATH


@pytest.mark.darwin
async def test_get_process_by_listening_port(client: DarwinClient) -> None:
    # there should only be one process listening on this port and that's us
    worker_process = await client.processes.get_by_pid(await client.get_pid())
    listening = await client.processes.get_processes_by_listening_port(DEFAULT_PORT)
    assert listening[0].pid == await worker_process.ppid()


@pytest.mark.darwin
async def test_process_object(client: DarwinClient) -> None:
    server = await client.processes.get_self()
    assert server.pid > 0
    images = await server.images()
    assert len(images) > 0
    server_path = await server.path()
    assert server_path is not None
    assert len([img for img in images if Path(img.path).name == Path(server_path).name]) > 0
    fds = await server.fds()
    assert fds[0].fd == 0
    assert fds[1].fd == 1
    assert fds[2].fd == 2


@pytest.mark.darwin
async def test_process_object_includes_shared_memory_fd(client: DarwinClient) -> None:
    shm_name = f"/rpc-{uuid4().hex[:8]}"
    fd = (await client.symbols.shm_open(shm_name, O_RDWR | O_CREAT, 0o600)).c_int32
    if fd < 0:
        await client.raise_errno_exception(f"shm_open({shm_name}) failed")

    try:
        server = await client.processes.get_self()
        shm_fds = [item for item in await server.fds() if isinstance(item, SharedMemoryFd)]
        assert any(item.fd == fd and item.path == shm_name for item in shm_fds)
    finally:
        if await client.symbols.close(fd) != 0:
            await client.raise_errno_exception(f"close({fd}) failed")
        if await client.symbols.shm_unlink(shm_name) != 0:
            await client.raise_errno_exception(f"shm_unlink({shm_name}) failed")


@pytest.mark.darwin
async def test_get_memgraph_snapshot(client: DarwinClient) -> None:
    server = await client.processes.get_self()
    parent = await server.parent()
    assert len(await parent.get_memgraph_snapshot()) > 0


@pytest.mark.ios
async def test_launch_process(client: IosClient) -> None:
    process = await client.processes.launch("com.apple.calculator")
    await process.kill()


@pytest.mark.ios
async def test_launch_invalid_process(client: IosClient) -> None:
    with pytest.raises(LaunchError):
        await client.processes.launch("com.apple.cyber")
