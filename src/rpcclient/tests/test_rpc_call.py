import pytest

from rpcclient.client_manager import ClientManager
from rpcclient.core.client import ClientEvent
from rpcclient.exceptions import ServerResponseError, UnexpectedReplyError
from rpcclient.protocol.messages import resolve_request
from rpcclient.protos.rpc_api_pb2 import REQ_DLOPEN, ReplyDlopen, ReplyListDir, RequestDlopen, RequestListDir
from rpcclient.protos.rpc_pb2 import Handshake, RpcMessage
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


async def test_rpc_call_unexpected_reply_terminates_client(monkeypatch: pytest.MonkeyPatch) -> None:
    async def reply_to_another_request(msg: RpcMessage) -> RpcMessage:
        return RpcMessage(client_id=msg.client_id, msg_id=msg.msg_id + 1)

    # not the `client` fixture: its teardown would try to use the connection this test terminates
    client = await ClientManager().create(hostname="127.0.0.1")
    terminated = []
    client.notifier.register(ClientEvent.TERMINATED, terminated.append)
    monkeypatch.setattr(client._bridge.sock, "rpc_msg_send_recv", reply_to_another_request)
    with pytest.raises(UnexpectedReplyError, match=r"to rpc\.api\.RequestListDir"):
        await client.rpc_call(RequestListDir(path="/"))

    assert terminated == [client.id]
    assert client._bridge.sock.raw_socket.fileno() == -1
