import logging
import threading
from typing import Callable, Type, Union

from rpcclient.clients.ios.client import IosClient
from rpcclient.clients.linux.client import LinuxClient
from rpcclient.clients.macos.client import MacosClient
from rpcclient.core.client import ClientEvent, CoreClient
from rpcclient.core.protosocket import ProtoSocket
from rpcclient.event_notifier import EventNotifier
from rpcclient.registry import Registry
from rpcclient.transports import create_local, create_tcp

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

        self.transport_factory = Registry[str, Callable[..., ProtoSocket]]({
            'tcp': create_tcp,
            'local': create_local,
        })

        self._lock = threading.RLock()
        self._clients: Registry[int, ClientType] = Registry(notifier=self.notifier)

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
        client.notifier.register(ClientEvent.TERMINATED, self._on_client_terminated)
        client.notifier.register(ClientEvent.CREATED, self._on_client_created)
        self.add(client)

        return client

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
