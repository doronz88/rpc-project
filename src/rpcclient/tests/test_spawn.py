from io import StringIO

import pytest


@pytest.mark.parametrize('argv,expected_stdout,errorcode', [
    [['/bin/echo', 'blat'], 'blat', 0],
    [['/bin/ls', 'INVALID_PATH'], 'ls: INVALID_PATH: No such file or directory', 256],
])
def test_spawn_sanity(client, argv, expected_stdout, errorcode):
    stdout = StringIO()
    assert errorcode == client.spawn(argv, stdout=stdout, stdin=b'')

    stdout.seek(0)
    assert expected_stdout == stdout.read().strip()


def test_spawn_bad_value_stress(client):
    for i in range(1000):
        assert 256 == client.spawn(['/bin/ls', 'INVALID_PATH'], stdout=StringIO(), stdin=b'')
