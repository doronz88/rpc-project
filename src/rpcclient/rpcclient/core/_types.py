from typing import TYPE_CHECKING, Generic, TypeVar


if TYPE_CHECKING:
    from rpcclient.core.client import AsyncCoreClient, BaseCoreClient, CoreClient
    from rpcclient.core.symbol import AsyncSymbol, BaseSymbol, Symbol


ClientT_co = TypeVar("ClientT_co", bound="BaseCoreClient[BaseSymbol]", covariant=True)
SyncClientT_co = TypeVar("SyncClientT_co", bound="CoreClient[Symbol]", covariant=True)
AsyncClientT_co = TypeVar("AsyncClientT_co", bound="AsyncCoreClient[AsyncSymbol]", covariant=True)
SymbolT_co = TypeVar("SymbolT_co", bound="BaseSymbol", covariant=True)


class ClientBound(Generic[ClientT_co]):
    _client: ClientT_co

    def __zync_proxy__(self: "ClientBound[BaseCoreClient[SymbolT_co]]") -> SymbolT_co:
        return self._client.null


class SymbolBound(Generic[SymbolT_co]):
    _symbol: SymbolT_co

    def __zync_proxy__(self: "SymbolBound[SymbolT_co]") -> SymbolT_co:
        return self._symbol
