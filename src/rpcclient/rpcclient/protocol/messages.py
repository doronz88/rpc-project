import logging
from typing import Any, Type

from rpcclient.protos.rpc_pb2 import ProtocolConstants, ReplyError
from rpcclient.registry import Registry

logger = logging.getLogger(__name__)


class RpcMessageRegistry(Registry[int, Type[Any]]):
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

    def __init__(self, modules=None):
        super().__init__()
        self.register(ProtocolConstants.REP_ERROR, ReplyError)
        for module in modules:
            self.update(self.load_by_module(module))

    @staticmethod
    def load_by_module(module_path: str) -> dict[int, Type[Any]]:

        import importlib
        mod = importlib.import_module(module_path)

        # Use the module descriptor for robust access to enum values
        enum_desc = mod.DESCRIPTOR.enum_types_by_name['MsgId']
        msg_id_to_class = {}

        def _to_camel(s: str) -> str:
            # "DLSYM" -> "Dlsym", "DUMMY_BLOCK" -> "DummyBlock"
            return ''.join(p.capitalize() for p in s.lower().split('_'))

        for enum_value in enum_desc.values:
            name = enum_value.name
            value = enum_value.number
            if not name.startswith('REQ_'):
                continue
            camel = _to_camel(name.split('_', 1)[1])
            req_class = getattr(mod, f'Request{camel}', None)
            rep_class = getattr(mod, f'Reply{camel}', None)
            if req_class is None or rep_class is None:
                logger.warning(
                    f'Skipping {name}: missing Request{camel} or Reply{camel} in {module_path}'
                )
            msg_id_to_class[value] = req_class
            msg_id_to_class[value + ProtocolConstants.RPC_MAX_REQ_MSG_ID] = rep_class
        logger.debug(
            f'Loaded {len(msg_id_to_class) / 2} bindings from {module_path}'
        )
        return msg_id_to_class
