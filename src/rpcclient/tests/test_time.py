from datetime import datetime

import pytest

from rpcclient.clients.darwin.client import DarwinClient


pytestmark = pytest.mark.darwin


async def test_now(client: DarwinClient) -> None:
    assert await client.time.now() > datetime.fromtimestamp(0)


async def test_set_current(client: DarwinClient) -> None:
    old_now = await client.time.now()
    try:
        await client.time.set_current(datetime(year=2020, month=1, day=1))
        assert await client.time.now() < datetime(year=2020, month=1, day=1, minute=1)
    finally:
        await client.time.set_current(old_now)
        await client.time.set_auto()


async def test_is_set_automatically(client: DarwinClient) -> None:
    await client.time.set_auto()
    assert await client.time.is_set_automatically()
