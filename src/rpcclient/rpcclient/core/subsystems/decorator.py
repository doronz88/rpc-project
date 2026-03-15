import logging
from collections.abc import Callable
from typing import Any, Generic, TypeVar, overload
from typing_extensions import Self

from rpcclient.exceptions import ServerDiedError, SubsystemInitError


logger = logging.getLogger(__name__)


class SubsystemNotAvailable:
    """Null-object for an unavailable subsystem."""

    __slots__ = ("name", "reason")

    def __init__(self, name: str, reason: str | BaseException = "Not supported") -> None:
        """Store the subsystem name and the failure reason."""
        self.name = name
        self.reason = str(reason)

    def __bool__(self) -> bool:
        """Always False so `if obj.subsystem:` is skipped."""
        return False

    def __getattr__(self, attr: str) -> Any:
        """Raise a clear error on any attribute access."""
        raise SubsystemInitError(f"Subsystem '{self.name}' is not available: {self.reason}")

    def __repr__(self) -> str:
        """Debug-friendly representation."""
        return f"<SubsystemNotAvailable {self.name}: {self.reason}>"


SubsystemT_co = TypeVar("SubsystemT_co", covariant=True)
SelfT = TypeVar("SelfT")
SelfT_co = TypeVar("SelfT_co", covariant=True)


class subsystem(Generic[SelfT_co, SubsystemT_co]):
    """Descriptor that lazily initializes a subsystem and caches the result."""

    def __init__(self, fget: Callable[[SelfT_co], SubsystemT_co]) -> None:
        """Capture the factory callable and set cache metadata."""
        self.fget: Callable[[SelfT_co], SubsystemT_co] = fget
        self.__doc__ = getattr(fget, "__doc__", None)
        self.name: str = fget.__name__
        self.cache_key: str = f"_{self.name}"

    def __set_name__(self, owner: type, name: str) -> None:
        """Bind the descriptor name and derive the cache key."""
        self.name = name
        self.cache_key = f"_{name}"

    @overload
    def __get__(self, instance: None, owner: type) -> Self: ...
    @overload
    def __get__(self: "subsystem[SelfT, SubsystemT_co]", instance: SelfT, owner: type | None) -> SubsystemT_co: ...
    def __get__(self, instance: Any, owner: type | None = None) -> Self | SubsystemT_co | SubsystemNotAvailable:
        """Build on first access, cache, and return; wrap failures as NotAvailable."""
        if instance is None:
            return self
        d = instance.__dict__
        if self.cache_key in d:
            return d[self.cache_key]
        try:
            value = self.fget(instance)
        except Exception as e:
            if isinstance(e, ServerDiedError):
                raise
            logger.exception("Subsystem %s failed to initialize", self.name)
            value = SubsystemNotAvailable(self.name, e)
        d[self.cache_key] = value
        return value
