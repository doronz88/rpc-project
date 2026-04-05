from datetime import datetime

import pytest

from rpcclient.clients.darwin.client import DarwinClient


pytestmark = pytest.mark.darwin


def test_now(client: DarwinClient) -> None:
    assert client.time.now() > datetime.fromtimestamp(0)


def test_set_current(client: DarwinClient) -> None:
    old_now = client.time.now()
    try:
        client.time.set_current(datetime(year=2020, month=1, day=1))
        assert client.time.now() < datetime(year=2020, month=1, day=1, minute=1)
    finally:
        client.time.set_current(old_now)
        client.time.set_auto()


def test_is_set_automatically(client: DarwinClient) -> None:
    client.time.set_auto()
    assert client.time.is_set_automatically
