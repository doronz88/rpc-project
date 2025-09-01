from contextlib import closing

from rpcclient.client_manager import ClientManager


def test_new_process_per_client(client):
    with closing(ClientManager().create(hostname='127.0.0.1')) as client2:
        assert client.pid != client2.pid
        client_process = client.processes.get_by_pid(client.pid)
        client2_process = client2.processes.get_by_pid(client2.pid)
        assert client_process.ppid == client2_process.ppid
