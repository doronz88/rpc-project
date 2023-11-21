import pytest

from rpcclient.exceptions import RpcPermissionError

pytestmark = pytest.mark.darwin


def test_query_certificates(client):
    try:
        assert len(client.keychain.query_certificates()) > 1
    except RpcPermissionError:
        pass


def test_query_keys(client):
    try:
        assert len(client.keychain.query_keys()) > 1
    except RpcPermissionError:
        pass
