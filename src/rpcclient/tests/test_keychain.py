import contextlib

import pytest

from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.exceptions import RpcPermissionError


pytestmark = pytest.mark.darwin


async def test_query_certificates(client: DarwinClient) -> None:
    with contextlib.suppress(RpcPermissionError):
        assert len(await client.keychain.query_certificates()) > 1


async def test_query_keys(client: DarwinClient) -> None:
    with contextlib.suppress(RpcPermissionError):
        assert len(await client.keychain.query_keys()) > 1
