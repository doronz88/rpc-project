from tests._types import SyncClient


def test_valid_gethostbyname(client: SyncClient) -> None:
    assert client.network.gethostbyname("google.com") is not None


def test_invalid_gethostbyname(client: SyncClient) -> None:
    assert client.network.gethostbyname("google.com1") is None
