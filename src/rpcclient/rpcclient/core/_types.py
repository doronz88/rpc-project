from typing import TYPE_CHECKING, Generic, TypeVar


if TYPE_CHECKING:
    from rpcclient.core.client import CoreClient
    from rpcclient.core.symbol import Symbol


ClientT_co = TypeVar("ClientT_co", bound="CoreClient[Symbol]", covariant=True)
SymbolT_co = TypeVar("SymbolT_co", bound="Symbol", covariant=True)


class ClientBound(Generic[ClientT_co]):
    _client: ClientT_co


class SymbolBound(Generic[SymbolT_co]):
    _symbol: SymbolT_co
