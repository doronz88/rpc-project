import contextlib

import pytest

from rpcclient.exceptions import RpcPermissionError

pytestmark = pytest.mark.darwin


def test_query_certificates(client):
    with contextlib.suppress(RpcPermissionError):
        assert len(client.keychain.query_certificates()) > 1


def test_query_keys(client):
    with contextlib.suppress(RpcPermissionError):
        assert len(client.keychain.query_keys()) > 1
