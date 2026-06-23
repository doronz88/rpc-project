import pytest

from rpcclient.clients.darwin.client import DarwinClient


pytestmark = pytest.mark.darwin


async def test_duet_knowledge_store(client: DarwinClient) -> None:
    async with await client.duet.knowledge_store() as ctx:
        events = await ctx.query_events_streams()
        assert events.keys() != 0
