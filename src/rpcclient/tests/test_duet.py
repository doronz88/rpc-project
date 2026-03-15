import pytest

from rpcclient.clients.darwin.client import DarwinClient


pytestmark = pytest.mark.darwin


def test_duet_knowledge_store(client: DarwinClient) -> None:
    with client.duet.knowledge_store() as ctx:
        events = ctx.query_events_streams()
        assert events.keys() != 0
