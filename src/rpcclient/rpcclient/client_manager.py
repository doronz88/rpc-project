import logging
import threading
from typing import Callable, Type, Union

from rpcclient.clients.ios.client import IosClient
from rpcclient.clients.linux.client import LinuxClient
from rpcclient.clients.macos.client import MacosClient
from rpcclient.core.client import CoreClient
from rpcclient.core.protosocket import ProtoSocket
from rpcclient.event_notifier import EventNotifier, EventType
from rpcclient.registries import SingleRegistry
from rpcclient.transports import create_local, create_tcp

logger = logging.getLogger(__name__)
ClientType = Union[IosClient, MacosClient, LinuxClient, CoreClient]
ClientClass = Type[ClientType]


class ClientManager:
    """ Manage client lifecycle and dispatch client-related events. """

    def __init__(self) -> None:
        """ Initialize registries, notifier, and register default factories/transports. """
        self._lock = threading.RLock()
        self._clients: SingleRegistry = SingleRegistry()
        self.notifier = EventNotifier()
        self.client_factory = SingleRegistry[str, ClientClass]({
            'ios': IosClient,
            'osx': MacosClient,
            'linux': LinuxClient,
            'core': CoreClient,
        })

        self.transport_factory = SingleRegistry[str, Callable[..., ProtoSocket]]({
            'tcp': create_tcp,
            'local': create_local,
        })

    def create(self, mode: str = 'tcp', **kwargs) -> ClientType:
        """ Create a client via transport `mode`, resolve platform, store, and emit CREATED. """
        transport_factory = self.transport_factory.get(mode)
        if transport_factory is None:
            raise ValueError(f'Unknown client mode: {mode}')

        proto_sock = transport_factory(**kwargs)
        server_type = proto_sock.handshake.platform.lower()

        client_factory = self.client_factory.get(server_type)
        if client_factory is None:
            raise ValueError(f'Unknown client mode: {server_type}')

        client: ClientType = client_factory(
            cid=proto_sock.handshake.client_id,
            sock=proto_sock,
            sysname=proto_sock.handshake.sysname.lower(),
            arch=proto_sock.handshake.arch,
            server_type=server_type
        )
        client.notifier.register(EventType.CLIENT_DISCONNECTED, self._on_client_disconnect)

        self._clients.register(client.id, client)
        self.notifier.notify(EventType.CLIENT_CREATED, client)
        return client

    def remove(self, cid: int) -> bool:
        """ Remove a client by ID; emit REMOVED if found. """
        removed = self._clients.unregister(cid)
        if removed is not None:
            self.notifier.notify(EventType.CLIENT_REMOVED, cid)
            return True
        return False

    def clear(self) -> None:
        """ Remove all clients (prunes the registry and emits REMOVED per client). """
        for cid, _ in self._clients.items():
            self.remove(cid)

    def get(self, cid: int) -> Union[ClientType, None]:
        """ Return the client for ID, or None. """
        return self._clients.get(cid)

    @property
    def clients(self) -> dict[int, ClientType]:
        return dict(self._clients.items())

    def _on_client_disconnect(self, cid: int) -> None:
        """ Internal: remove a client when it signals disconnection. """
        self.remove(cid)
