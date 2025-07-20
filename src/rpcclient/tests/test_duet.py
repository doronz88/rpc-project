

def test_duet_knowledge_store(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    with client.duet.knowledge_store() as ctx:
        events = ctx.query_events_streams()
        assert 0 != events.keys()
