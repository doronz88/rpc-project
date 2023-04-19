import pytest

pytestmark = pytest.mark.darwin


def test_query_certificates(client):
    assert len(client.keychain.query_certificates()) > 1


def test_query_keys(client):
    assert len(client.keychain.query_keys()) > 1
