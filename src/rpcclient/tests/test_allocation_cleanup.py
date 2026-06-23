import gc

import pytest

from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.core.subsystems.fs import RemotePath


@pytest.mark.darwin
async def test_allocate_file_fd_context_manager(client: DarwinClient, tmp_path: RemotePath[DarwinClient]) -> None:
    # make sure when the test starts, all previous Allocated references are freed
    gc.collect()
    fds_count = len(await (await client.processes.get_by_pid(await client.get_pid())).fds())
    async with await client.fs.open(tmp_path / "test", "w"):
        assert fds_count + 1 == len(await (await client.processes.get_by_pid(await client.get_pid())).fds())
    assert fds_count == len(await (await client.processes.get_by_pid(await client.get_pid())).fds())


@pytest.mark.darwin
async def test_allocate_file_fd_explicit_deallocate(client: DarwinClient, tmp_path: RemotePath[DarwinClient]) -> None:
    # make sure when the test starts, all previous Allocated references are freed
    gc.collect()
    fds_count = len(await (await client.processes.get_by_pid(await client.get_pid())).fds())
    fd = await client.fs.open(tmp_path / "test", "w")
    assert fds_count + 1 == len(await (await client.processes.get_by_pid(await client.get_pid())).fds())
    await fd.deallocate()
    assert fds_count == len(await (await client.processes.get_by_pid(await client.get_pid())).fds())


@pytest.mark.darwin
async def test_listdir_fd_release(client: DarwinClient) -> None:
    fds_count = len(await (await client.processes.get_by_pid(await client.get_pid())).fds())
    await client.fs.listdir("/")
    assert fds_count == len(await (await client.processes.get_by_pid(await client.get_pid())).fds())
