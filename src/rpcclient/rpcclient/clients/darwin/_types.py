from typing import TYPE_CHECKING, TypeVar


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient
    from rpcclient.clients.darwin.symbol import AsyncDarwinSymbol, BaseDarwinSymbol, DarwinSymbol


DarwinSymbolT = TypeVar("DarwinSymbolT", bound="BaseDarwinSymbol")
DarwinSymbolT_co = TypeVar("DarwinSymbolT_co", bound="BaseDarwinSymbol", covariant=True)
SyncDarwinSymbolT_co = TypeVar("SyncDarwinSymbolT_co", bound="DarwinSymbol", covariant=True)
AsyncDarwinSymbolT_co = TypeVar("AsyncDarwinSymbolT_co", bound="AsyncDarwinSymbol", covariant=True)

DarwinClientT = TypeVar("DarwinClientT", bound="BaseDarwinClient[BaseDarwinSymbol]")
DarwinClientT_co = TypeVar("DarwinClientT_co", bound="BaseDarwinClient[BaseDarwinSymbol]", covariant=True)
