import pytest

from rpcclient.client.client_factory import create_client


@pytest.fixture
def client():
    return create_client('127.0.0.1')
