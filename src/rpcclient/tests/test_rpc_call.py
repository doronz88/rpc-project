import pytest

from rpcclient.exceptions import ServerResponseError
from rpcclient.protocol.messages import resolve_request
from rpcclient.protos.rpc_api_pb2 import REQ_DLOPEN, ReplyDlopen, ReplyListDir, RequestDlopen, RequestListDir
from rpcclient.protos.rpc_pb2 import Handshake
from tests._types import Client


def test_resolve_request() -> None:
    assert resolve_request(RequestDlopen) == (REQ_DLOPEN, ReplyDlopen)


async def test_rpc_call_rejects_non_request(client: Client) -> None:
    with pytest.raises(ValueError, match=r"Not a request message: rpc\.Handshake"):
        await client.rpc_call(Handshake())


async def test_rpc_call_server_error(client: Client) -> None:
    with pytest.raises(ServerResponseError):
        await client.rpc_call(RequestListDir(path="/definitely/not/here"))

    # the error reply was consumed, so the next call gets its own reply
    assert isinstance(await client.rpc_call(RequestListDir(path="/")), ReplyListDir)
