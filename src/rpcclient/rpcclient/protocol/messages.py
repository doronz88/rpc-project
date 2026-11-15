import functools

from google.protobuf import message_factory
from google.protobuf.descriptor import Descriptor
from google.protobuf.message import Message

from rpcclient.protos.rpc_pb2 import ProtocolConstants


def _to_camel(s: str) -> str:
    # "DLSYM" -> "Dlsym", "DUMMY_BLOCK" -> "DummyBlock"
    return "".join(p.capitalize() for p in s.lower().split("_"))


@functools.cache
def resolve_request(request_class: type[Message]) -> tuple[int, type[Message]]:
    """
    Get the msg_id and reply class of a request message type.

    Both come from the request's own .proto file: `RequestX` is sent as `MsgId.REQ_X` and answered with `ReplyX`.
    """
    descriptor = request_class.DESCRIPTOR
    if not descriptor.name.startswith("Request"):
        raise ValueError(f"Not a request message: {descriptor.full_name}")
    camel = descriptor.name.removeprefix("Request")

    file = descriptor.file
    enum_desc = file.enum_types_by_name.get("MsgId")
    msg_id = None
    for value in enum_desc.values if enum_desc else ():
        if value.name.startswith("REQ_") and _to_camel(value.name.removeprefix("REQ_")) == camel:
            msg_id = value.number

    reply_desc = file.message_types_by_name.get(f"Reply{camel}")
    # Descriptor's isinstance() also accepts the upb implementation's descriptors
    if msg_id is None or not isinstance(reply_desc, Descriptor):
        raise ValueError(f"{descriptor.full_name}: {file.name} has no matching MsgId.REQ_* value or Reply{camel}")

    # Same bounds as the server's routine_lookup() (rpcserver/routines.c)
    if msg_id <= 0 or msg_id >= ProtocolConstants.RPC_MAX_REQ_MSG_ID:
        raise ValueError(f"Invalid msg_id: {msg_id}")

    return msg_id, message_factory.GetMessageClass(reply_desc)
