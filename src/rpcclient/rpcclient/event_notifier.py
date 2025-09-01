import logging
from enum import Enum, auto
from typing import Any

from rpcclient.registries import MultiRegistry

logger = logging.getLogger(__name__)


class EventType(Enum):
    """ Event identifiers for the client lifecycle. """
    CLIENT_CREATED = auto()
    CLIENT_REMOVED = auto()
    CLIENT_DISCONNECTED = auto()


class EventNotifier(MultiRegistry):
    """ Notifies registered callbacks when events occur. """

    def notify(self, event: EventType, *args: Any, **kwargs: Any) -> None:
        """ Invoke all callbacks registered for the given event. """
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
