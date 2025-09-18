import logging
import threading
from typing import Callable, Type, Union

from rpcclient.clients.ios.client import IosClient
from rpcclient.clients.linux.client import LinuxClient
from rpcclient.clients.macos.client import MacosClient
from rpcclient.core.client import ClientEvent, CoreClient
from rpcclient.event_notifier import EventNotifier
from rpcclient.protocol.rpc_bridge import RpcBridge
from rpcclient.registry import Registry
from rpcclient.transports import create_local, create_tcp, create_using_protocol
from rpcclient.utils import prompt_selection

logger = logging.getLogger(__name__)
ClientType = Union[IosClient, MacosClient, LinuxClient, CoreClient]
ClientClass = Type[ClientType]


class ClientManager:
    """ Manage client lifecycle and dispatch client-related events. """

    def __init__(self) -> None:
        """ Initialize registries, notifier, and register default factories/transports. """
        self.notifier = EventNotifier()
        self.client_factory = Registry[str, ClientClass]({
            'ios': IosClient,
            'osx': MacosClient,
            'linux': LinuxClient,
            'core': CoreClient,
        })

        self.transport_factory = Registry[str, Callable[..., RpcBridge]]({
            'tcp': create_tcp,
            'local': create_local,
            'protocol': create_using_protocol,
        })

        self._lock = threading.RLock()
        self._clients: Registry[int, ClientType] = Registry(notifier=self.notifier)

    def create(self, mode: str = 'tcp', **kwargs) -> ClientType:
        """ Create a client via transport `mode`, resolve platform, store, and emit CREATED. """
        transport_factory = self.transport_factory.get(mode)
        if transport_factory is None:
            raise ValueError(f'Unknown client mode: {mode}')

        # If using protocol-based spawn/routing and no explicit client provided,
        # try to pick a capable existing client (with create_worker).
        if mode == 'protocol' and 'client' not in kwargs:
            kwargs['client'] = self._select_capable_client()

        rpc_bridge = transport_factory(**kwargs)
        server_type = rpc_bridge.platform

        client_factory = self.client_factory.get(server_type)
        if client_factory is None:
            raise ValueError(f'Unknown client mode: {server_type}')

        client: ClientType = client_factory(bridge=rpc_bridge)
        client.notifier.register(ClientEvent.TERMINATED, self._on_client_terminated)
        client.notifier.register(ClientEvent.CREATED, self._on_client_created)
        self.add(client)

        return client

    def _select_capable_client(self):
        capable = [c for c in self.clients.values() if hasattr(c, 'create_worker') and callable(getattr(c, 'create_worker'))]
        if not capable:
            raise ValueError('No existing client supports protocol worker creation.')
        if len(capable) == 1:
            return capable[0]
        else:
            return prompt_selection(capable, 'Select a client client ID')

    def add(self, client: ClientType) -> None:
        self._clients.register(client.id, client)

    def remove(self, cid: int) -> None:
        """ Remove a client by ID; emit REMOVED if found. """
        self._clients.unregister(cid)

    def clear(self) -> None:
        """ Remove all clients. """
        self._clients.clear()

    def get(self, cid: int) -> Union[ClientType, None]:
        """ Return the client for ID, or None. """
        return self._clients.get(cid)

    @property
    def clients(self) -> dict[int, ClientType]:
        return dict(self._clients.items())

    # ---------------------------------------------------------------------------
    # Client Event callbacks
    # ---------------------------------------------------------------------------

    def _on_client_terminated(self, cid: int) -> None:
        """ Internal: remove a client when it terminates. """
        self.remove(cid)

    def _on_client_created(self, client: ClientType) -> None:
        """ Internal: Add a client when if created by another client. """
        self.add(client)
