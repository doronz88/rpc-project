from typing import TypeAlias

from rpcclient.core.client import AsyncCoreClient, CoreClient
from rpcclient.core.symbol import AsyncSymbol, Symbol


SyncClient: TypeAlias = CoreClient[Symbol]
AsyncClient: TypeAlias = AsyncCoreClient[AsyncSymbol]
