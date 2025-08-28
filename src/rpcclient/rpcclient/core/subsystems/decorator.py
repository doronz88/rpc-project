import logging
from typing import Any, Callable, Union

from rpcclient.exceptions import ServerDiedError, SubsystemInitError

logger = logging.getLogger(__name__)


class SubsystemNotAvailable:
    """ Null-object for an unavailable subsystem. """
    __slots__ = ("name", "reason")

    def __init__(self, name: str, reason: Union[str, BaseException] = "Not supported") -> None:
        """ Store the subsystem name and the failure reason. """
        self.name = name
        self.reason = str(reason)

    def __bool__(self) -> bool:
        """ Always False so `if obj.subsystem:` is skipped. """
        return False

    def __getattr__(self, attr: str) -> Any:
        """ Raise a clear error on any attribute access. """
        raise SubsystemInitError(f"Subsystem '{self.name}' is not available: {self.reason}")

    def __repr__(self) -> str:
        """ Debug-friendly representation. """
        return f"<SubsystemNotAvailable {self.name}: {self.reason}>"


class subsystem:
    """ Descriptor that lazily initializes a subsystem and caches the result. """

    def __init__(self, fget: Callable[[Any], Any]) -> None:
        """ Capture the factory callable and set cache metadata. """
        self.fget = fget
        self.__doc__ = getattr(fget, "__doc__", None)
        self.name = fget.__name__
        self.cache_key = f"_{self.name}"

    def __set_name__(self, owner: type, name: str) -> None:
        """ Bind the descriptor name and derive the cache key. """
        self.name = name
        self.cache_key = f"_{name}"

    def __get__(self, obj: Any, objtype: Union[type, None] = None) -> Any:
        """ Build on first access, cache, and return; wrap failures as NotAvailable. """
        if obj is None:
            return self
        d = obj.__dict__
        if self.cache_key in d:
            return d[self.cache_key]
        try:
            value = self.fget(obj)
        except Exception as e:  # noqa: BLE001
            if isinstance(e, ServerDiedError):
                raise
            logger.error("Subsystem %s failed to initialize: %s", self.name, e)
            value = SubsystemNotAvailable(self.name, e)
        d[self.cache_key] = value
        return value
