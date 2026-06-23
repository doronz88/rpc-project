from typing import TypeAlias

from rpcclient.core.client import CoreClient
from rpcclient.core.symbol import Symbol


Client: TypeAlias = CoreClient[Symbol]
# Back-compat aliases (the sync/async split no longer exists).
SyncClient: TypeAlias = Client
AsyncClient: TypeAlias = Client
