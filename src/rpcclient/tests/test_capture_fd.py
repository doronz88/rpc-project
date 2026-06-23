import pytest

from rpcclient.clients.darwin.client import DarwinClient


STDOUT_FD = 1
STDERR_FD = 2
TEST_DATA: bytes = b"testtesttest"


@pytest.mark.darwin
@pytest.mark.parametrize("fd", [STDOUT_FD, STDERR_FD])
async def test_capture_fd(client: DarwinClient, fd: int) -> None:
    async with client.capture_fd(fd) as cap:
        if await client.symbols.write(fd, TEST_DATA, len(TEST_DATA)) == -1:
            await client.raise_errno_exception("write to fd failed")
        data = await cap.read()
    assert data == TEST_DATA


@pytest.mark.darwin
@pytest.mark.parametrize("fd", [STDOUT_FD, STDERR_FD])
async def test_fd_cleanup(client: DarwinClient, fd: int) -> None:
    fd_count = len(await (await client.processes.get_self()).fds())
    async with client.capture_fd(fd):
        pass
    assert fd_count == len(await (await client.processes.get_self()).fds())
