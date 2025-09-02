import logging
import threading
from typing import Any, Callable, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)

E = TypeVar("E")
Callback = Callable[..., Any]


class EventNotifier(Generic[E]):
    """ Notifies registered callbacks when events occur """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: dict[E, set[Callback]] = {}

    def register(self, event: E, callback: Callback) -> None:
        """ Register a callback for an event """
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            self._data.setdefault(event, set()).add(callback)

    def unregister(self, event: E, callback: Callback) -> bool:
        """ Unregister a callback; returns True if it was present """
        with self._lock:
            s = self._data.get(event)
            if not s:
                return False
            try:
                s.remove(callback)
                if not s:
                    self._data.pop(event, None)
                return True
            except KeyError:
                return False

    def register_once(self, event: E, callback: Callback) -> None:
        """ Register a callback that will be invoked at most once """

        def _wrapper(*args: Any, **kwargs: Any) -> None:
            try:
                callback(*args, **kwargs)
            finally:
                # ensure we remove even if callback raises
                self.unregister(event, _wrapper)

        self.register(event, _wrapper)

    def clear(self, event: Optional[E] = None) -> None:
        """ Remove all callbacks (optionally only for one event) """
        with self._lock:
            if event is None:
                self._data.clear()
            else:
                self._data.pop(event, None)

    def listeners(self, event: E) -> tuple[Callback, ...]:
        """ Return current listeners for an event (snapshot) """
        with self._lock:
            return tuple(self._data.get(event, ()))

    def has_listeners(self, event: E) -> bool:
        with self._lock:
            s = self._data.get(event)
            return bool(s)

    def notify(self, event: E, *args: Any, **kwargs: Any) -> None:
        """ Invoke all callbacks registered for the given event """
        with self._lock:
            callbacks = self._data.get(event, set()).copy()

        for callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception:
                logger.error(
                    "Error in callback %s for event %r",
                    getattr(callback, "__name__", repr(callback)),
                    event,
                    exc_info=True,
                )
