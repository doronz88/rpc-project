import abc
import logging
from typing import Generic, TypeVar

import zyncio

from rpcclient.clients.ios.client import AsyncIosClient, IosClient
from rpcclient.clients.linux.client import AsyncLinuxClient, LinuxClient
from rpcclient.clients.macos.client import AsyncMacosClient, MacosClient
from rpcclient.core.client import AsyncCoreClient, BaseCoreClient, ClientEvent, CoreClient
from rpcclient.core.symbol import AsyncSymbol, Symbol
from rpcclient.event_notifier import EventNotifier
from rpcclient.protocol.rpc_bridge import AsyncRpcBridge, SyncRpcBridge
from rpcclient.registry import Registry
from rpcclient.transports import create_local, create_tcp, create_using_protocol
from rpcclient.utils import prompt_selection


logger = logging.getLogger(__name__)

ClientT = TypeVar("ClientT", bound=BaseCoreClient)


class BaseClientManager(Generic[ClientT], zyncio.ZyncBase, abc.ABC):
    """Manage client lifecycle and dispatch client-related events."""

    def __init__(self) -> None:
        """Initialize registries, notifier, and register default factories/transports."""
        self.notifier: EventNotifier = EventNotifier()
        self.client_factory: Registry[str, type[ClientT]] = self._init_client_factory_registry()

        self.transport_factory: Registry[str, zyncio.zfunc[..., SyncRpcBridge | AsyncRpcBridge]] = Registry({
            "tcp": create_tcp,
            "local": create_local,
            "protocol": create_using_protocol,
        })

        self._clients: Registry[int, ClientT] = Registry(notifier=self.notifier)

    @abc.abstractmethod
    def _init_client_factory_registry(self) -> Registry[str, type[ClientT]]: ...

    @zyncio.zmethod
    async def create(self, mode: str = "tcp", internal: bool = False, **kwargs) -> ClientT:
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

        rpc_bridge = await transport_factory.run_zync(self.__zync_mode__, **kwargs)
        server_type = rpc_bridge.platform
        cached = self.get(rpc_bridge.client_id)
        if cached is not None:
            return cached

        client_factory = self.client_factory.get(server_type)
        if client_factory is None:
            raise ValueError(f"Unknown client mode: {server_type}")

        client: ClientT = await client_factory.create.z(bridge=rpc_bridge)
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

    def add(self, client: ClientT, internal: bool = False) -> None:
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

    def get(self, cid: int) -> ClientT | None:
        """Return the client for ID, or None."""
        return self._clients.get(cid)

    @property
    def clients(self) -> dict[int, ClientT]:
        return dict(self._clients.items())

    # ---------------------------------------------------------------------------
    # Client Event callbacks
    # ---------------------------------------------------------------------------

    def _on_client_terminated(self, cid: int) -> None:
        """Internal: remove a client when it terminates."""
        self.remove(cid)

    def _on_client_created(self, client: ClientT) -> None:
        """Internal: Add a client when if created by another client."""
        self.add(client)


class ClientManager(zyncio.SyncMixin, BaseClientManager[CoreClient[Symbol]]):
    def _init_client_factory_registry(self) -> Registry[str, type[CoreClient]]:
        return Registry[str, type[CoreClient]]({
            "ios": IosClient,
            "osx": MacosClient,
            "linux": LinuxClient,
            "core": CoreClient,
        })


class AsyncClientManager(zyncio.AsyncMixin, BaseClientManager[AsyncCoreClient[AsyncSymbol]]):
    def _init_client_factory_registry(self) -> Registry[str, type[AsyncCoreClient]]:
        return Registry[str, type[AsyncCoreClient]]({
            "ios": AsyncIosClient,
            "osx": AsyncMacosClient,
            "linux": AsyncLinuxClient,
            "core": AsyncCoreClient,
        })
