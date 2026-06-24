import pytest

from rpcclient.clients.darwin.client import DarwinClient


pytestmark = pytest.mark.darwin


async def test_from_xpc_object(client: DarwinClient) -> None:
    criteria = await client.symbols.xpc_dictionary_create(0, 0, 0)
    await client.symbols.xpc_dictionary_set_int64(criteria, "Delay", 5)
    await client.symbols.xpc_dictionary_set_int64(criteria, "GracePeriod", 1)
    await client.symbols.xpc_dictionary_set_string(criteria, "Priority", "Utility")
    assert await client.xpc.decode_xpc_object_using_cf_serialization(criteria) == {
        "Delay": 5,
        "Priority": "Utility",
        "GracePeriod": 1,
    }
