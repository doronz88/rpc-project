import pytest

pytestmark = pytest.mark.darwin


def test_modules(client):
    """
    :param rpcclient.client.Client client:
    """
    assert '/usr/lib/libSystem.B.dylib' in client.modules


def test_uname(client):
    """
    :param rpcclient.client.Client client:
    """
    assert client.uname.sysname == 'Darwin'
    assert 'machine' in client.uname
