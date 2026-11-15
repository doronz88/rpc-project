import functools
import importlib
import logging
from typing import Any

from google.protobuf import message_factory
from google.protobuf.descriptor import Descriptor
from google.protobuf.message import Message

from rpcclient.protos.rpc_api_pb2 import ReplyError
from rpcclient.protos.rpc_pb2 import ProtocolConstants
from rpcclient.registry import Registry


logger = logging.getLogger(__name__)


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


class RpcMessageRegistry:
    """
    Handles the registration of RPC message mappings.

    This class extends the Registry to manage mappings between unique integer
    protocol message IDs and their corresponding request/response message
    types. It provides utilities for dynamically loading these message
    mappings from specified modules, ensuring a streamlined mechanism for
    message resolution. The typical usage involves initializing the class,
    potentially with module paths, where message definitions are declared.

    Methods:
        load_by_module: Dynamically loads message ID to class mappings from the provided module.

    """

    def __init__(self, init_data: dict | None = None, modules: list[str] | None = None) -> None:
        self._messages: Registry[int, type[Any]] = Registry()
        self._messages.register(ProtocolConstants.REP_ERROR, ReplyError)
        if init_data is None:
            init_data = {}
        if modules is None:
            modules = []
        self._messages.update(init_data)
        for module in modules:
            self.load_from_module(module)

    def load_from_module(self, module_path: str) -> None:
        mod = importlib.import_module(module_path)

        # Use the module descriptor for robust access to enum values
        enum_desc = mod.DESCRIPTOR.enum_types_by_name["MsgId"]

        pair_count = 0
        for enum_value in enum_desc.values:
            name = enum_value.name
            value = enum_value.number
            if not name.startswith("REQ_"):
                continue
            camel = _to_camel(name.split("_", 1)[1])
            req_class = getattr(mod, f"Request{camel}", None)
            rep_class = getattr(mod, f"Reply{camel}", None)
            if req_class is None or rep_class is None:
                logger.warning(f"Skipping {name}: missing Request{camel} or Reply{camel} in {module_path}")
                continue
            pair_count += 1
            self.register_pair(value, req_class, rep_class)
        logger.debug(f"Loaded {pair_count} bindings from {module_path}")

    def register_pair(self, msg_id: int, req_class: type[Any], rep_class: type[Any]) -> None:
        if msg_id > ProtocolConstants.RPC_MAX_REQ_MSG_ID:
            raise ValueError(f"Invalid msg_id: {msg_id}")
        self._messages.register(msg_id, req_class)
        self._messages.register(msg_id + ProtocolConstants.RPC_MAX_REQ_MSG_ID, rep_class)

    def unregister_pair(self, msg_id: int) -> None:
        if msg_id > ProtocolConstants.RPC_MAX_REQ_MSG_ID:
            raise ValueError(f"Invalid msg_id: {msg_id}")
        self._messages.unregister(msg_id)
        self._messages.unregister(msg_id + ProtocolConstants.RPC_MAX_REQ_MSG_ID)

    def update(self, data: dict, overwrite: bool = False) -> None:
        self._messages.update(data, overwrite)

    def clone(self) -> "RpcMessageRegistry":
        new_registry = RpcMessageRegistry()
        new_registry.update(dict(self._messages.items()), overwrite=True)
        return new_registry

    def get(self, msg_id: int) -> type[Any]:
        msg_class = self._messages.get(msg_id)
        if msg_class is None:
            raise ValueError(f"Unknown msg_id: {msg_id}")
        return msg_class

    def clear(self) -> None:
        self._messages.clear()
