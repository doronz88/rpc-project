import pytest

pytestmark = pytest.mark.darwin


def test_modules(client):
    """
    :param rpcclient.client.Client client:
    """
    assert '/usr/lib/libSystem.B.dylib' in [module.name for module in client.images]


def test_uname(client):
    """
    :param rpcclient.client.Client client:
    """
    assert client.uname.sysname == 'Darwin'
    assert 'machine' in client.uname


def test_get_class_list(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    assert len(client.get_class_list()) > 0


def test_load_framework(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    assert client.load_framework('Foundation') != 0


def test_load_all_libraries(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    original_count = len(client.images)
    client.load_all_libraries()
    assert len(client.images) > original_count
