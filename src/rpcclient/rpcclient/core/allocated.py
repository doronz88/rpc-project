import abc
from typing_extensions import Self

from rpcclient.core._types import ClientBound, ClientT_co


class Allocated(ClientBound[ClientT_co], abc.ABC):
    """resource allocated on remote host that needs to be free"""

    _allocated: bool = False
    _deallocated: bool = False

    async def __aenter__(self) -> Self:
        await self.allocate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.deallocate()

    async def _allocate(self) -> None:
        pass

    async def allocate(self) -> None:
        if not self._allocated:
            self._allocated = True
            await self._allocate()

    @abc.abstractmethod
    async def _deallocate(self) -> None:
        pass

    async def deallocate(self) -> None:
        if not self._deallocated:
            self._deallocated = True
            await self._deallocate()
