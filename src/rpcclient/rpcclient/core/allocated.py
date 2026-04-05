import abc
from typing import TYPE_CHECKING, TypeVar
from typing_extensions import Self

import zyncio

from rpcclient.core._types import ClientBound, ClientT_co


if TYPE_CHECKING:
    from rpcclient.core.client import BaseCoreClient
    from rpcclient.core.symbol import AsyncSymbol, Symbol


SyncAllocatedT_co = TypeVar("SyncAllocatedT_co", bound="Allocated[BaseCoreClient[Symbol]]")
AsyncAllocatedT_co = TypeVar("AsyncAllocatedT_co", bound="Allocated[BaseCoreClient[AsyncSymbol]]")


class Allocated(ClientBound[ClientT_co], abc.ABC):
    """resource allocated on remote host that needs to be free"""

    _allocated: bool = False
    _deallocated: bool = False

    def __enter__(self: SyncAllocatedT_co) -> SyncAllocatedT_co:
        """Enter in sync mode."""
        self.allocate()
        return self

    async def __aenter__(self) -> Self:
        """Enter in async (or zync) mode."""
        await self.allocate.z()
        return self

    def __exit__(self: "Allocated[BaseCoreClient[Symbol]]", exc_type, exc_val, exc_tb) -> None:
        self.deallocate()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.deallocate.z()

    async def _allocate(self) -> None:
        pass

    @zyncio.zmethod
    async def allocate(self) -> None:
        if not self._allocated:
            self._allocated = True
            await self._allocate()

    @abc.abstractmethod
    async def _deallocate(self) -> None:
        pass

    @zyncio.zmethod
    async def deallocate(self) -> None:
        if not self._deallocated:
            self._deallocated = True
            await self._deallocate()
