from tests._types import SyncClient


async def test_valid_gethostbyname(client: SyncClient) -> None:
    assert await client.network.gethostbyname("google.com") is not None


async def test_invalid_gethostbyname(client: SyncClient) -> None:
    assert await client.network.gethostbyname("google.com1") is None


async def test_interfaces(client: SyncClient) -> None:
    interfaces = await client.network.interfaces()
    assert any(interface.address == "127.0.0.1" for interface in interfaces)
