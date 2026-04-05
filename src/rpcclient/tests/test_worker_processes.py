import pytest

from rpcclient.client_manager import ClientManager
from rpcclient.clients.darwin.client import DarwinClient


@pytest.mark.darwin
def test_new_process_per_client(client: DarwinClient) -> None:
    with ClientManager().create(hostname="127.0.0.1") as client2:
        assert isinstance(client2, DarwinClient)
        assert client.pid != client2.pid
        client_process = client.processes.get_by_pid(client.pid)
        client2_process = client2.processes.get_by_pid(client2.pid)
        assert client_process.ppid == client2_process.ppid
