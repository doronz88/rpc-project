import pytest

from rpcclient.clients.darwin.client import DarwinClient


pytestmark = pytest.mark.darwin


def test_from_xpc_object(client: DarwinClient) -> None:
    criteria = client.symbols.xpc_dictionary_create(0, 0, 0)
    client.symbols.xpc_dictionary_set_int64(criteria, "Delay", 5)
    client.symbols.xpc_dictionary_set_int64(criteria, "GracePeriod", 1)
    client.symbols.xpc_dictionary_set_string(criteria, "Priority", "Utility")
    assert client.xpc.decode_xpc_object_using_cf_serialization(criteria) == {
        "Delay": 5,
        "Priority": "Utility",
        "GracePeriod": 1,
    }
