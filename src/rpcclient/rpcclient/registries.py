import threading
from collections import defaultdict
from typing import Generic, List, Optional, Set, Tuple, TypeVar, Union

K = TypeVar('K')
T = TypeVar('T')
V = TypeVar('V')


class SingleRegistry(Generic[K, V]):
    """ Thread-safe 1:1 registry (key -> value). """

    def __init__(self, initial_data: Optional[dict[K, V]] = None) -> None:
        self._lock = threading.RLock()
        self._data: dict[K, V] = {}

        if initial_data is not None:
            for key, value in initial_data.items():
                self._data[key] = value

    def register(self, key: K, value: V) -> None:
        """ Add or replace a value for key. """
        with self._lock:
            self._data[key] = value

    def unregister(self, key: K) -> Optional[V]:
        """ Remove the key and return its value, or None if missing. """
        with self._lock:
            return self._data.pop(key, None)

    def get(self, key: K) -> Optional[V]:
        """ Get value for a key, or None if missing. """
        with self._lock:
            return self._data.get(key)

    def items(self) -> list[tuple[K, V]]:
        """ Snapshot of all (key, value) pairs. """
        with self._lock:
            return list(self._data.items())

    def clear(self) -> None:
        """ Remove all entries. """
        with self._lock:
            self._data.clear()

    def __contains__(self, key: K) -> bool:
        """ Return True if the key exists. """
        with self._lock:
            return key in self._data


class MultiRegistry(Generic[K, V]):
    """ Thread-safe 1:N registry (key -> set(values)). """

    def __init__(self, initial_data: Optional[dict[K, Union[set[V], list[V]]]] = None) -> None:
        self._lock = threading.RLock()
        self._data: dict[K, set[V]] = defaultdict(set)

        if initial_data is not None:
            for key, values in initial_data.items():
                # Handle both set and list inputs
                value_set = values if isinstance(values, set) else set(values)
                self._data[key] = value_set

    def register(self, key: K, value: V) -> None:
        """ Add value to the set under a key. """
        with self._lock:
            self._data[key].add(value)

    def unregister(self, key: K, value: V) -> bool:
        """ Remove value from the key's set. Returns True if removed. """
        with self._lock:
            s = self._data.get(key)
            if not s or value not in s:
                return False
            s.remove(value)
            if not s:
                self._data.pop(key, None)
            return True

    def get(self, key: K) -> Set[V]:
        """ Return a copy of the set for a key (empty if missing). """
        with self._lock:
            return set(self._data.get(key, set()))

    def items(self) -> List[Tuple[K, Set[V]]]:
        """ Snapshot of all (key, set(values)) pairs. """
        with self._lock:
            return [(k, set(vs)) for k, vs in self._data.items()]

    def clear(self) -> None:
        """ Remove all entries. """
        with self._lock:
            self._data.clear()

    def __contains__(self, key: K) -> bool:
        """ Return True if the key exists. """
        with self._lock:
            return key in self._data
