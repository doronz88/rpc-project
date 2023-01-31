import pytest

from rpcclient.exceptions import ArgumentError


def test_peek(client):
    """
    :param rpcclient.client.Client client:
    """
    with client.safe_malloc(0x100) as peekable:
        client.peek(peekable, 0x100)


def test_poke(client):
    """
    :param rpcclient.client.Client client:
    """
    with client.safe_malloc(0x100) as peekable:
        client.poke(peekable, b'a' * 0x100)


def test_peek_invalid_address(client):
    """
    :param rpcclient.client.Client client:
    """
    with pytest.raises(ArgumentError):
        client.peek(0, 0x10)


def test_poke_invalid_address(client):
    """
    :param rpcclient.client.Client client:
    """
    with pytest.raises(ArgumentError):
        client.poke(0, b'a')


def test_get_dummy_block(client):
    """
    :param rpcclient.client.Client client:
    """
    assert client.get_dummy_block() != 0


def test_listdir(client):
    """
    :param rpcclient.client.Client client:
    """
    entries = client.listdir('/')
    assert entries[0].d_name == '.'
    assert entries[1].d_name == '..'


def test_calloc(client):
    """
    :param rpcclient.client.Client client:
    """
    with client.safe_calloc(0x100) as zeros:
        assert client.peek(zeros, 0x100) == b'\x00' * 0x100


def test_env_get_set(client):
    """
    :param rpcclient.client.Client client:
    """
    client.setenv('TEST', 'test')
    assert client.getenv('TEST') == 'test'


def test_environ(client):
    """
    :param rpcclient.client.Client client:
    """
    assert len(client.environ) > 0
    for e in client.environ:
        assert '=' in e


def test_reconnect(client):
    """
    :param rpcclient.client.Client client:
    """
    test_listdir(client)
    client.reconnect()
    test_listdir(client)
