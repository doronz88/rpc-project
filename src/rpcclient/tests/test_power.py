import pytest

from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.clients.darwin.consts import IOPMUserActiveType


pytestmark = pytest.mark.darwin


async def test_copy_assertions_status(client: DarwinClient) -> None:
    assertions = await client.power.copy_assertions_status()
    assert len(assertions) > 0


async def test_copy_assertions_by_process(client: DarwinClient) -> None:
    await client.power.copy_assertions_by_process()


async def test_declare_user_activity(client: DarwinClient) -> None:
    name = "test user activity"
    async with await client.power.declare_user_activity(name, IOPMUserActiveType.kIOPMUserActiveLocal):
        assert (await client.power.copy_assertions_by_process())[await client.get_pid()][0]["AssertName"] == name


async def test_declare_user_network_activity(client: DarwinClient) -> None:
    name = "test user network activity"
    async with await client.power.declare_network_client_activity(name):
        assert (await client.power.copy_assertions_by_process())[await client.get_pid()][0]["AssertName"] == name


async def test_create_assertion(client: DarwinClient) -> None:
    name = "test assertion"
    async with await client.power.create_assertion(name, "PreventUserIdleSystemSleep"):
        assert (await client.power.copy_assertions_by_process())[await client.get_pid()][0]["AssertName"] == name
