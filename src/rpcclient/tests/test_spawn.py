from io import StringIO

import pytest

from rpcclient.clients.darwin.client import DarwinClient
from tests._types import SyncClient


@pytest.mark.darwin
async def test_spawn_fds(client: DarwinClient) -> None:
    pid = (await client.spawn(["/bin/sleep", "5"], stdout=StringIO(), stdin="", background=True)).pid

    # should only have: stdin, stdout and stderr
    assert len(await (await client.processes.get_by_pid(pid)).fds()) == 3

    await client.processes.kill(pid)


@pytest.mark.local_only
@pytest.mark.parametrize(
    ("argv", "expected_stdout", "success"),
    [
        [["/bin/sleep", "0"], "", True],
        [["/bin/echo", "blat"], "blat", True],
        [["/bin/ls", "INVALID_PATH"], "No such file or directory", False],
    ],
)
async def test_spawn_foreground_sanity(
    client: SyncClient, argv: list[str], expected_stdout: str, success: bool
) -> None:
    stdout = StringIO()
    if success:
        assert (await client.spawn(argv, stdout=stdout, stdin="")).error == 0
    else:
        assert (await client.spawn(argv, stdout=stdout, stdin="")).error != 0
    stdout.seek(0)
    assert expected_stdout in stdout.read().strip()


@pytest.mark.local_only
@pytest.mark.parametrize(
    ("argv", "expected_stdout", "success"),
    [
        [["/bin/sleep", "0"], "", True],
        [["/bin/echo", "blat"], "blat", True],
        [["/bin/ls", "INVALID_PATH"], "No such file or directory", False],
    ],
)
async def test_spawn_foreground_stress(
    client: SyncClient, argv: list[str], expected_stdout: str, success: bool
) -> None:
    for _i in range(100):
        await test_spawn_foreground_sanity(client, argv, expected_stdout, success)


async def test_spawn_background_sanity(client: SyncClient) -> None:
    spawn_result = await client.spawn(["/bin/sleep", "5"], stdout=StringIO(), stdin="", background=True)

    # when running in background, no error is returned
    assert spawn_result.error is None
    assert spawn_result.stdout is None

    # instead, we can just make sure it ran by sending it a kill and don't fail
    await client.processes.kill(spawn_result.pid)


async def test_spawn_background_stress(client):
    for _i in range(100):
        await test_spawn_background_sanity(client)
