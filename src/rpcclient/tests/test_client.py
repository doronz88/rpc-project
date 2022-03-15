import pytest

from rpcclient.exceptions import ArgumentError


def test_peek(client):
    """
    :param rpcclient.client.Client client:
    """
    with client.safe_malloc(0x100) as peekable:
        client.peek(peekable, 0x100)


def test_peek_invalid_address(client):
    """
    :param rpcclient.client.Client client:
    """
    with pytest.raises(ArgumentError):
        client.peek(0, 0x10)


def test_calloc(client):
    """
    :param rpcclient.client.Client client:
    """
    with client.safe_calloc(0x100) as zeros:
        assert client.peek(zeros, 0x100) == b'\x00' * 0x100
