import threading
from enum import Enum, auto
from typing import Generic, Optional, TypeVar

from rpcclient.event_notifier import EventNotifier

K = TypeVar('K')
V = TypeVar('V')


class RegistryEvent(Enum):
    """ Event identifiers for registry operations. """
    REGISTERED = auto()
    UNREGISTERED = auto()
    CLEARED = auto()


class Registry(Generic[K, V]):
    """ Thread-safe 1:1 registry (key -> value). """

    def __init__(self, initial_data: Optional[dict[K, V]] = None, notifier: Optional[EventNotifier] = None) -> None:
        self._lock = threading.RLock()
        self._data: dict[K, V] = {}
        self.notifier: EventNotifier = notifier or EventNotifier()

        if initial_data is not None:
            self._data.update(initial_data)

    def register(self, key: K, value: V) -> None:
        """ Add or replace a value for a key. """
        with self._lock:
            self._data[key] = value
        self.notifier.notify(RegistryEvent.REGISTERED, *(key, value))

    def unregister(self, key: K) -> Optional[V]:
        """ Remove the key """
        with self._lock:
            self._data.pop(key, None)
        self.notifier.notify(RegistryEvent.UNREGISTERED, key)

    def clear(self) -> None:
        """ Remove all entries. """
        with self._lock:
            self._data.clear()
        self.notifier.notify(RegistryEvent.CLEARED)

    def get(self, key: K) -> Optional[V]:
        """ Get value for a key, or None if missing. """
        with self._lock:
            return self._data.get(key)

    def items(self) -> list[tuple[K, V]]:
        """ Snapshot of all (key, value) pairs. """
        with self._lock:
            return list(self._data.items())

    def __contains__(self, key: K) -> bool:
        """ Return True if the key exists. """
        with self._lock:
            return key in self._data
