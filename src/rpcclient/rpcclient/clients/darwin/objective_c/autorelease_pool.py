from collections import UserList
from typing import TYPE_CHECKING
from typing_extensions import Self

from construct import Hex, Int32ul, PaddedString, Struct

from rpcclient.clients.darwin._types import DarwinClientT_co, DarwinSymbolT, DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.core.structs.generic import SymbolFormatField


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient


magic_t = Struct("m0" / Hex(Int32ul), "m1" / PaddedString(12, "ascii"))


SIZEOF_PAGE_DATA = 0x38


def AutoreleasePoolPageData(client: "DarwinClient") -> Struct:
    return Struct(
        "magic" / magic_t,
        "next" / SymbolFormatField(client),
        "thread" / SymbolFormatField(client),
        "parent" / SymbolFormatField(client),
        "child" / SymbolFormatField(client),
        "depth" / Hex(Int32ul),
        "hiwat" / Hex(Int32ul),
    )


class AutoreleasePool(UserList[DarwinSymbolT], ClientBound["DarwinClient[DarwinSymbolT]"]):
    """
    A list-like container for `DarwinSymbol` objects representing one Objective-C autorelease pool.
    """

    def __init__(self, client: "DarwinClient[DarwinSymbolT]", address: DarwinSymbolT, mask: int) -> None:
        """
        Initialize `AutoreleasePool`.

        :param client:
        :param address: address of the pool start.
        """
        super().__init__()
        self._client = client
        self.address: DarwinSymbolT = address
        self.end: DarwinSymbolT = address + 8
        self._mask: int = mask

    @classmethod
    async def create(
        cls, client: "DarwinClient[DarwinSymbolT]", address: DarwinSymbolT
    ) -> "AutoreleasePool[DarwinSymbolT]":
        mask = await client.symbols.objc_debug_autoreleasepoolpage_ptr_mask.getindex(0)
        pool = cls(client, address, mask)
        await pool.refresh()
        return pool

    async def refresh(self) -> None:
        """
        refresh the content of of the `AutoreleasePool` object to reflect the current state of the actual pool
        """
        self.clear()
        await get_autorelease_pool_end(self._client)  # to solve autorelease pool bug
        page_sym = await find_page_for_address(self.address)
        page = await page_sym.parse(AutoreleasePoolPageData(self._client))
        next_address = self.address + 8
        while (await next_address.getindex(0)).c_int64 not in [
            0,
            0xA3A3A3A3,
            0xA3A3A3A3A3A3A3A3,
        ] or next_address == page.next:
            if next_address == page.next:
                if page.child == 0:
                    break
                next_address = page.child + SIZEOF_PAGE_DATA
                page = AutoreleasePoolPageData(self._client).parse_stream(page.child)
                continue
            self.append(await next_address.getindex(0) & self._mask)
            next_address += 8
        self.end = next_address

    def __repr__(self) -> str:
        """
        Return human-readable representation showing pool name and object count.

        :return: String representation of the pool
        """
        return f"<{self.__class__.__name__} {hex(self.address)} contains {len(self)} objects>"

    async def display(self) -> str:
        output = f"{self.__class__.__name__} {hex(self.address)}:\n"
        for idx, sym in enumerate(self):
            class_name = await (await self._client.symbols.class_getName(await sym.objc_call("class"))).peek_str()
            output += f"#{idx}:\t0x{sym:x}\t{class_name}\n"

        return output

    def __str__(self) -> str:
        """
        Return string representation showing pool name all of the objects inside.

        :return: String representation of the pool
        """
        return self.__repr__()


class AutorelesePoolCtx(ClientBound[DarwinClientT_co]):
    """
    Context manager to create and drain an Objective-C `NSAutoreleasePool`.

    On enter: creates a new pool.
    On exit: drains (releases) the pool.
    """

    def __init__(self, client: DarwinClientT_co) -> None:
        """
        Initialize `AutorelesePoolCtx`.

        :param client:
        """
        self._client = client
        self._pool = None

    async def __aenter__(self) -> Self:
        """
        Ensure a fresh pool exists when entering `with` block.

        :return: Self reference for the context manager
        """
        await self._create()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Drain the pool when exiting `with` block.
        """
        await self.drain()

    async def _create(self) -> None:
        """
        Create the pool if not already present.
        """
        if self._pool is None:
            self._pool = await self._client.symbols.objc_autoreleasePoolPush()

    async def drain(self) -> None:
        """
        Drain (release) the current autorelease pool if it exists, then clear it.
        """
        if self._pool is not None:
            await self._client.symbols.objc_autoreleasePoolPop(self._pool)
            self._pool = None

    async def get_autorelease_pool(self) -> AutoreleasePool | None:
        """
        Return an `AutoreleasePool` object representing the current pool.

        :return: `AutoreleasePool` instance if pool is initialized, else None
        """
        if self._pool is not None:
            return await AutoreleasePool.create(self._client, self._pool)
        return None


async def get_autorelease_pool_end(client: "DarwinClient[DarwinSymbolT_co]") -> "DarwinSymbolT_co":
    """
    Retreive the end of the autorelease pool.

    :param client:
    :return: `DarwinSymbol` representing the end of the pool
    """
    end = await client.symbols.objc_autoreleasePoolPush()
    await client.symbols.objc_autoreleasePoolPop(end)
    return end


async def find_page_for_address(address: "DarwinSymbolT_co") -> "DarwinSymbolT_co":
    """
    Find the page for a given address inside of the thread's autorelease pool.

    :param client:
    :param address: An address inside of the autorelease pool
    :return: `DarwinSymbol` representing page
    """
    current = address - SIZEOF_PAGE_DATA
    while await current.peek(4) != b"\xa1\xa1\xa1\xa1":
        current -= 8
    return current


async def find_hot_page(client: "DarwinClient[DarwinSymbolT_co]") -> DarwinSymbolT_co:
    """
    Find the current hot page of the thread's autorelease pool.

    :param client:
    :return: `DarwinSymbol` representing the end of the pool
    """
    return await find_page_for_address(await get_autorelease_pool_end(client))


async def find_first_page(client: "DarwinClient[DarwinSymbolT_co]") -> DarwinSymbolT_co:
    """
    Find the current first page of the thread's autorelease pool.

    :param client:
    :return: `DarwinSymbol` representing the end of the pool
    """
    page_sym = await find_hot_page(client)
    page = await page_sym.parse(AutoreleasePoolPageData(client))
    while page.parent != 0:
        page_sym = page.parent
        page = await page_sym.parse(AutoreleasePoolPageData(client))
    return page_sym


async def get_autorelease_pools(client: "DarwinClient[DarwinSymbolT]") -> list[AutoreleasePool[DarwinSymbolT]]:
    """
    Get and parse all autorelease pools currently in the thread.

    :param client:
    :return: List of `AutoreleasePool` instances found in the dump
    """
    end = await get_autorelease_pool_end(client)
    page_sym = await find_first_page(client)
    pool = await AutoreleasePool.create(client, page_sym + SIZEOF_PAGE_DATA)
    pools: list[AutoreleasePool] = [pool]
    while pool.end != end:
        pool = await AutoreleasePool.create(client, pool.end)
        pools.append(pool)
    return pools


async def get_current_autorelease_pool(client: "DarwinClient[DarwinSymbolT]") -> AutoreleasePool[DarwinSymbolT]:
    """
    Get the most recently created autorelease pool.

    :param client:
    :return: The last `AutoreleasePool` in the list (most recent)
    :raises IndexError: if no pools are found
    """
    return (await get_autorelease_pools(client))[-1]
