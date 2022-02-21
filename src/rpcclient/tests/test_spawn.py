from io import StringIO

import pytest


@pytest.mark.parametrize('argv,expected_stdout,errorcode', [
    [['/bin/echo', 'blat'], 'blat', 0],
    [['/bin/ls', 'INVALID_PATH'], 'ls: INVALID_PATH: No such file or directory', 256],
])
def test_spawn_sanity(client, argv, expected_stdout, errorcode):
    stdout = StringIO()
    assert errorcode == client.spawn(argv, stdout=stdout, stdin=b'').error

    stdout.seek(0)
    assert expected_stdout == stdout.read().strip()


def test_spawn_bad_value_stress(client):
    for i in range(100):
        stdout = StringIO()
        assert 256 == client.spawn(['/bin/ls', 'INVALID_PATH'], stdout=stdout, stdin=b'').error

        stdout.seek(0)
        assert 'ls: INVALID_PATH: No such file or directory' == stdout.read().strip()


def test_spawn_background(client):
    spawn_result = client.spawn(['/bin/sleep', '5'], stdout=StringIO(), stdin=b'', background=True)

    # when running in background, no error is returned
    assert spawn_result.error is None

    # instead, we can just make sure it ran by sending it a kill and don't fail
    client.processes.kill(spawn_result.pid)
