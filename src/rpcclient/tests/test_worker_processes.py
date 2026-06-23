import pytest

from rpcclient.client_manager import ClientManager
from rpcclient.clients.darwin.client import DarwinClient


@pytest.mark.darwin
async def test_new_process_per_client(client: DarwinClient) -> None:
    async with await ClientManager().create(hostname="127.0.0.1") as client2:
        assert isinstance(client2, DarwinClient)
        assert await client.get_pid() != await client2.get_pid()
        client_process = await client.processes.get_by_pid(await client.get_pid())
        client2_process = await client2.processes.get_by_pid(await client2.get_pid())
        assert await client_process.ppid() == await client2_process.ppid()
