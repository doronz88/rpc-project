from typing import TYPE_CHECKING, TypeVar


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient
    from rpcclient.clients.darwin.symbol import DarwinSymbol


DarwinSymbolT = TypeVar("DarwinSymbolT", bound="DarwinSymbol")
DarwinSymbolT_co = TypeVar("DarwinSymbolT_co", bound="DarwinSymbol", covariant=True)
SyncDarwinSymbolT_co = TypeVar("SyncDarwinSymbolT_co", bound="DarwinSymbol", covariant=True)
AsyncDarwinSymbolT_co = TypeVar("AsyncDarwinSymbolT_co", bound="DarwinSymbol", covariant=True)

DarwinClientT = TypeVar("DarwinClientT", bound="DarwinClient[DarwinSymbol]")
DarwinClientT_co = TypeVar("DarwinClientT_co", bound="DarwinClient[DarwinSymbol]", covariant=True)
