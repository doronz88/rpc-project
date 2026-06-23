from tests._types import SyncClient


async def test_valid_gethostbyname(client: SyncClient) -> None:
    assert await client.network.gethostbyname("google.com") is not None


async def test_invalid_gethostbyname(client: SyncClient) -> None:
    assert await client.network.gethostbyname("google.com1") is None
