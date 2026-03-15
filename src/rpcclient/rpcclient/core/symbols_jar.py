from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Final, Generic, Literal, TypeVar, overload
from typing_extensions import Self

import zyncio

from rpcclient.core._types import ClientBound
from rpcclient.core.symbol import AsyncSymbol, BaseSymbol, Symbol
from rpcclient.exceptions import SymbolAbsentError


if TYPE_CHECKING:
    from rpcclient.core.client import BaseCoreClient, RemoteCallArg


SymbolT = TypeVar("SymbolT", bound=BaseSymbol)
SymbolT_co = TypeVar("SymbolT_co", bound=BaseSymbol, covariant=True)
SyncSymbolT_co = TypeVar("SyncSymbolT_co", bound=Symbol, covariant=True)
AsyncSymbolT_co = TypeVar("AsyncSymbolT_co", bound=AsyncSymbol, covariant=True)


class SymbolsJar(ClientBound["BaseCoreClient[SymbolT_co]"], Generic[SymbolT_co]):
    __slots__ = ("_client", "_dict")

    __zync_mode__: None = None  # Prevent RecursionError due to __getattr__

    def __init__(self, client: "BaseCoreClient[SymbolT_co]") -> None:
        self._client = client
        self._dict: dict[str, SymbolT_co] = {}

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self._dict!r}>"

    @zyncio.zmethod
    async def get_lazy(self, name: str) -> SymbolT_co:
        sym = await self._client.dlsym.z(self._client._dlsym_global_handle, name)
        if sym == 0:
            raise SymbolAbsentError(f"no such loaded symbol: {name}")
        self._dict[name] = self._client.symbol(sym)
        return self._dict[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._dict)

    def __len__(self) -> int:
        return len(self._dict)

    @overload
    def __getitem__(self: "SymbolsJar[SyncSymbolT_co]", key: str) -> SyncSymbolT_co: ...
    @overload
    def __getitem__(
        self: "SymbolsJar[AsyncSymbolT_co]", key: str
    ) -> "AsyncSymbolT_co | LazySymbol[AsyncSymbolT_co]": ...
    @overload
    def __getitem__(self, key: str) -> "SymbolT_co | LazySymbol[SymbolT_co]": ...
    def __getitem__(self, key: str) -> "BaseSymbol | LazySymbol[BaseSymbol]":
        if key not in self._dict:
            if zyncio.is_sync(self):
                return self.get_lazy(key)
            return LazySymbol(self._client, key)

        return self._dict[key]

    __getattr__ = __getitem__

    def __setitem__(self, key: str, value: int) -> None:
        if key in self.__slots__:
            super().__setattr__(key, value)
        else:
            self._dict[key] = self._client.symbol(value)

    __setattr__ = __setitem__

    def __delitem__(self, key: str) -> None:
        del self._dict[key]

    __delattr__ = __delitem__

    def __sub__(self, other: Self) -> Self:
        retval = type(self)(self._client)
        for k1, v1 in self._dict.items():
            if k1 not in other:
                retval._dict[k1] = v1
        return retval

    def __add__(self, other: Self) -> Self:
        retval = type(self)(self._client)
        retval._dict.update(other._dict)
        retval._dict.update(self._dict)
        return retval


class LazySymbol(Generic[SymbolT_co]):
    def __init__(self, client: "BaseCoreClient[SymbolT_co]", name: str) -> None:
        self._client: Final[BaseCoreClient[SymbolT_co]] = client
        self.name: Final[str] = name

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name!r} of {self._client}>"

    async def resolve(self) -> SymbolT_co:
        return await self._client.symbols.get_lazy.z(self.name)

    async def getindex(self, index: int, *indices: int) -> SymbolT_co:
        return await (await self.resolve()).getindex(index, *indices)

    async def setindex(self, index: int, value) -> None:
        await (await self.resolve()).setindex(index, value)

    @overload
    async def call(
        self,
        *args: "RemoteCallArg",
        return_float64: Literal[False] = False,
        return_float32: Literal[False] = False,
        return_raw: Literal[False] = False,
        va_list_index: int | None = None,
    ) -> SymbolT_co: ...
    @overload
    async def call(
        self, *args: "RemoteCallArg", return_float64: Literal[True], va_list_index: int | None = None
    ) -> float: ...
    @overload
    async def call(
        self, *args: "RemoteCallArg", return_float32: Literal[True], va_list_index: int | None = None
    ) -> float: ...
    @overload
    async def call(
        self, *args: "RemoteCallArg", return_raw: Literal[True], va_list_index: int | None = None
    ) -> Any: ...
    @overload
    async def call(self, *args: "RemoteCallArg", **kwargs) -> float | Self | Any: ...
    async def call(self, *args: "RemoteCallArg", **kwargs) -> float | Self | Any:
        sym = await self.resolve()
        return await sym.call(*args, **kwargs)

    z = call
    """Alias for `call`, to match `BaseSymbol` and other zyncio-callables."""

    __call__ = call
