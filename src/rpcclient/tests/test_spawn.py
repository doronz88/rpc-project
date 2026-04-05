from io import StringIO

import pytest

from rpcclient.clients.darwin.client import DarwinClient
from tests._types import SyncClient


@pytest.mark.darwin
def test_spawn_fds(client: DarwinClient) -> None:
    pid = client.spawn(["/bin/sleep", "5"], stdout=StringIO(), stdin="", background=True).pid

    # should only have: stdin, stdout and stderr
    assert len(client.processes.get_by_pid(pid).fds) == 3

    client.processes.kill(pid)


@pytest.mark.local_only
@pytest.mark.parametrize(
    ("argv", "expected_stdout", "success"),
    [
        [["/bin/sleep", "0"], "", True],
        [["/bin/echo", "blat"], "blat", True],
        [["/bin/ls", "INVALID_PATH"], "No such file or directory", False],
    ],
)
def test_spawn_foreground_sanity(client: SyncClient, argv: list[str], expected_stdout: str, success: bool) -> None:
    stdout = StringIO()
    if success:
        assert client.spawn(argv, stdout=stdout, stdin="").error == 0
    else:
        assert client.spawn(argv, stdout=stdout, stdin="").error != 0
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
def test_spawn_foreground_stress(client: SyncClient, argv: list[str], expected_stdout: str, success: bool) -> None:
    for _i in range(100):
        test_spawn_foreground_sanity(client, argv, expected_stdout, success)


def test_spawn_background_sanity(client: SyncClient) -> None:
    spawn_result = client.spawn(["/bin/sleep", "5"], stdout=StringIO(), stdin="", background=True)

    # when running in background, no error is returned
    assert spawn_result.error is None
    assert spawn_result.stdout is None

    # instead, we can just make sure it ran by sending it a kill and don't fail
    client.processes.kill(spawn_result.pid)


def test_spawn_background_stress(client):
    for _i in range(100):
        test_spawn_background_sanity(client)
