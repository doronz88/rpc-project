import logging
from collections.abc import Awaitable, Callable

from rpcclient.clients.ios.client import IosClient
from rpcclient.clients.linux.client import LinuxClient
from rpcclient.clients.macos.client import MacosClient
from rpcclient.core.client import ClientEvent, CoreClient
from rpcclient.core.symbol import Symbol
from rpcclient.event_notifier import EventNotifier
from rpcclient.protocol.rpc_bridge import RpcBridge
from rpcclient.registry import Registry
from rpcclient.transports import create_local, create_tcp, create_using_protocol
from rpcclient.utils import prompt_selection


logger = logging.getLogger(__name__)

ClientType = CoreClient[Symbol]


class ClientManager:
    """Manage client lifecycle and dispatch client-related events."""

    def __init__(self) -> None:
        """Initialize registries, notifier, and register default factories/transports."""
        self.notifier: EventNotifier = EventNotifier()
        self.client_factory: Registry[str, type[ClientType]] = Registry[str, type[ClientType]]({
            "ios": IosClient,
            "osx": MacosClient,
            "linux": LinuxClient,
            "core": CoreClient,
        })

        self.transport_factory: Registry[str, Callable[..., Awaitable[RpcBridge]]] = Registry({
            "tcp": create_tcp,
            "local": create_local,
            "protocol": create_using_protocol,
        })

        self._clients: Registry[int, ClientType] = Registry(notifier=self.notifier)

    async def create(self, mode: str = "tcp", internal: bool = False, **kwargs) -> ClientType:
        """
        Create a client via transport `mode`, resolve platform, store, and emit CREATED.

        :param mode: Transport mode, e.g. "tcp" or "protocol" (default: "tcp")
        :param internal: If True, supply the CREATED event with the internal flag (default: False)
        """
        transport_factory = self.transport_factory.get(mode)
        if transport_factory is None:
            raise ValueError(f"Unknown client mode: {mode}")

        # If using protocol-based spawn/routing and no explicit client provided,
        # try to pick a capable existing client (with create_worker).
        if mode == "protocol" and "client" not in kwargs:
            kwargs["client"] = self._select_capable_client()

        rpc_bridge = await transport_factory(**kwargs)
        server_type = rpc_bridge.platform
        cached = self.get(rpc_bridge.client_id)
        if cached is not None:
            return cached

        client_factory = self.client_factory.get(server_type)
        if client_factory is None:
            raise ValueError(f"Unknown client mode: {server_type}")

        client: ClientType = await client_factory.create(bridge=rpc_bridge)
        # Prime caches so the prompt/repr can render progname/pid synchronously. Every creation
        # path flows through here — CLI connect and interactive `mgr.create` alike.
        await client.get_progname()
        await client.get_pid()
        client.notifier.register(ClientEvent.TERMINATED, self._on_client_terminated)
        client.notifier.register(ClientEvent.CREATED, self._on_client_created)
        self.add(client, internal=internal)

        return client

    def _select_capable_client(self):
        capable = [c for c in self.clients.values() if callable(getattr(c, "create_worker", None))]
        if not capable:
            raise ValueError("No existing client supports protocol worker creation.")
        if len(capable) == 1:
            return capable[0]
        else:
            return prompt_selection(capable, "Select a client client ID")

    def add(self, client: ClientType, internal: bool = False) -> None:
        """
        Add a client to the registry; emit REGISTERED if successful.

        :param internal: If True, supply the REGISTERED event with the internal flag (default: False)
        """
        self._clients.register(client.id, client, internal=internal)

    def remove(self, cid: int) -> None:
        """Remove a client by ID; emit REMOVED if found."""
        self._clients.unregister(cid)

    def clear(self) -> None:
        """Remove all clients."""
        self._clients.clear()

    async def close_all(self) -> None:
        """Close all clients and remove them from the registry."""
        for client in list(self.clients.values()):
            try:
                await client.close()
            except Exception:
                logger.exception("Failed to close client %s", client.id)
        self.clear()

    def get(self, cid: int) -> ClientType | None:
        """Return the client for ID, or None."""
        return self._clients.get(cid)

    @property
    def clients(self) -> dict[int, ClientType]:
        return dict(self._clients.items())

    # ---------------------------------------------------------------------------
    # Client Event callbacks
    # ---------------------------------------------------------------------------

    def _on_client_terminated(self, cid: int) -> None:
        """Internal: remove a client when it terminates."""
        self.remove(cid)

    def _on_client_created(self, client: ClientType) -> None:
        """Internal: Add a client when if created by another client."""
        self.add(client)
