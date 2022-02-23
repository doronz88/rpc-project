from io import StringIO

import pytest


def test_spawn_fds(client):
    pid = client.spawn(['/bin/sleep', '5'], stdout=StringIO(), stdin='', background=True).pid

    # should only have: stdin, stdout and stderr
    assert len(client.processes.get_by_pid(pid).fds) == 3

    client.processes.kill(pid)


@pytest.mark.local_only
@pytest.mark.parametrize('argv,expected_stdout,errorcode', [
    [['/bin/sleep', '0'], '', 0],
    [['/bin/echo', 'blat'], 'blat', 0],
    [['/bin/ls', 'INVALID_PATH'], 'ls: INVALID_PATH: No such file or directory', 256],
])
def test_spawn_foreground_sanity(client, argv, expected_stdout, errorcode):
    stdout = StringIO()
    assert errorcode == client.spawn(argv, stdout=stdout, stdin='').error

    stdout.seek(0)
    assert expected_stdout == stdout.read().strip()


@pytest.mark.local_only
@pytest.mark.parametrize('argv,expected_stdout,errorcode', [
    [['/bin/sleep', '0'], '', 0],
    [['/bin/echo', 'blat'], 'blat', 0],
    [['/bin/ls', 'INVALID_PATH'], 'ls: INVALID_PATH: No such file or directory', 256],
])
def test_spawn_foreground_stress(client, argv, expected_stdout, errorcode):
    for i in range(1000):
        test_spawn_foreground_sanity(client, argv, expected_stdout, errorcode)


def test_spawn_background_sanity(client):
    spawn_result = client.spawn(['/bin/sleep', '5'], stdout=StringIO(), stdin='', background=True)

    # when running in background, no error is returned
    assert spawn_result.error is None
    assert spawn_result.stdout is None

    # instead, we can just make sure it ran by sending it a kill and don't fail
    client.processes.kill(spawn_result.pid)


def test_spawn_background_stress(client):
    for i in range(1000):
        test_spawn_background_sanity(client)
