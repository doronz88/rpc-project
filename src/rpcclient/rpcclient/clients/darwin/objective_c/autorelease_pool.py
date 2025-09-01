from collections import UserList
from typing import List, Optional

from construct import Hex, Int32ul, PaddedString, Struct

from rpcclient.clients.darwin.symbol import DarwinSymbol
from rpcclient.core.structs.generic import SymbolFormatField

magic_t = Struct(
    'm0' / Hex(Int32ul),
    'm1' / PaddedString(12, 'ascii')
)


SIZEOF_PAGE_DATA = 0x38


def AutoreleasePoolPageData(client) -> Struct:
    return Struct(
            'magic' / magic_t,
            'next' / SymbolFormatField(client),
            'thread' / SymbolFormatField(client),
            'parent' / SymbolFormatField(client),
            'child' / SymbolFormatField(client),
            'depth' / Hex(Int32ul),
            'hiwat' / Hex(Int32ul)
        )


class AutoreleasePool(UserList[DarwinSymbol]):
    """
    A list-like container for `DarwinSymbol` objects representing one Objective-C autorelease pool.
    """

    def __init__(self, client, address: DarwinSymbol) -> None:
        """
        Initialize `AutoreleasePool`.

        :param client:
        :param address: address of the pool start.
        """
        super().__init__()
        self._client = client
        self._mask = client.symbols.objc_debug_autoreleasepoolpage_ptr_mask[0]
        self.address = address
        self.end = address + 8
        self.refresh()

    def refresh(self) -> None:
        """
        refresh the content of of the `AutoreleasePool` object to reflect the current state of the actual pool
        """
        self.clear()
        get_autorelease_pool_end(self._client)  # to solve autorelease pool bug
        page_sym = find_page_for_address(self._client, self.address)
        page = AutoreleasePoolPageData(self._client).parse_stream(page_sym)
        next = self.address + 8
        while (next[0].c_int64 not in [0, 0xa3a3a3a3, 0xa3a3a3a3a3a3a3a3] or
               next == page.next):
            if next == page.next:
                if page.child == 0:
                    break
                next = page.child + SIZEOF_PAGE_DATA
                page = AutoreleasePoolPageData(self._client).parse_stream(
                    page.child)
                continue
            self.append(next[0] & self._mask)
            next += 8
        self.end = next

    def __repr__(self) -> str:
        """
        Return human-readable representation showing pool name and object count.

        :return: String representation of the pool
        """
        return f'<{self.__class__.__name__} {hex(self.address)} contains {len(self)} objects>'

    def __str__(self) -> str:
        """
        Return string representation showing pool name all of the objects inside.

        :return: String representation of the pool
        """
        output = f'{self.__class__.__name__} {hex(self.address)}:\n'
        for idx in range(len(self)):
            class_name = self._client.symbols.class_getName(self[idx].objc_call('class')).peek_str()
            output += f'#{idx}:\t0x{self[idx]:x}\t{class_name}\n'

        return output


class AutorelesePoolCtx:
    """
    Context manager to create and drain an Objective-C `NSAutoreleasePool`.

    On enter: creates a new pool.
    On exit: drains (releases) the pool.
    """

    def __init__(self, client) -> None:
        """
        Initialize `AutorelesePoolCtx`.

        :param client:
        """
        self._client = client
        self._pool = None
        self._create()

    def __enter__(self) -> 'AutorelesePoolCtx':
        """
        Ensure a fresh pool exists when entering `with` block.

        :return: Self reference for the context manager
        """
        self._create()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Drain the pool when exiting `with` block.
        """
        self.drain()

    def _create(self) -> None:
        """
        Create the pool if not already present.
        """
        if self._pool is None:
            self._pool = self._client.symbols.objc_autoreleasePoolPush()

    def drain(self) -> None:
        """
        Drain (release) the current autorelease pool if it exists, then clear it.
        """
        if self._pool is not None:
            self._client.symbols.objc_autoreleasePoolPop(self._pool)
            self._pool = None

    def get_autorelease_pool(self) -> Optional[AutoreleasePool]:
        """
        Return an `AutoreleasePool` object representing the current pool.

        :return: `AutoreleasePool` instance if pool is initialized, else None
        """
        if self._pool is not None:
            return AutoreleasePool(self._client, self._pool)
        return None


def get_autorelease_pool_end(client) -> DarwinSymbol:
    """
    Retreive the end of the autorelease pool.

    :param client:
    :return: `DarwinSymbol` representing the end of the pool
    """
    end = client.symbols.objc_autoreleasePoolPush()
    client.symbols.objc_autoreleasePoolPop(end)
    return end


def find_page_for_address(client, address: DarwinSymbol) -> DarwinSymbol:
    """
    Find the page for a given address inside of the thread's autorelease pool.

    :param client:
    :param address: An address inside of the autorelease pool
    :return: `DarwinSymbol` representing page
    """
    current = address - SIZEOF_PAGE_DATA
    while current.peek(4) != b'\xa1\xa1\xa1\xa1':
        current -= 8
    return current


def find_hot_page(client) -> DarwinSymbol:
    """
    Find the current hot page of the thread's autorelease pool.

    :param client:
    :return: `DarwinSymbol` representing the end of the pool
    """
    return find_page_for_address(client, get_autorelease_pool_end(client))


def find_first_page(client) -> DarwinSymbol:
    """
    Find the current first page of the thread's autorelease pool.

    :param client:
    :return: `DarwinSymbol` representing the end of the pool
    """
    page_sym = find_hot_page(client)
    page = AutoreleasePoolPageData(client).parse_stream(page_sym)
    while page.parent != 0:
        page_sym = page.parent
        page = AutoreleasePoolPageData(client).parse_stream(page_sym)
    return page_sym


def get_autorelease_pools(client) -> List[AutoreleasePool]:
    """
    Get and parse all autorelease pools currently in the thread.

    :param client:
    :return: List of `AutoreleasePool` instances found in the dump
    """
    end = get_autorelease_pool_end(client)
    page_sym = find_first_page(client)
    pool = AutoreleasePool(client, page_sym + SIZEOF_PAGE_DATA)
    pools: List[AutoreleasePool] = [pool]
    while pool.end != end:
        pool = AutoreleasePool(client, pool.end)
        pools.append(pool)
    return pools


def get_current_autorelease_pool(client) -> AutoreleasePool:
    """
    Get the most recently created autorelease pool.

    :param client:
    :return: The last `AutoreleasePool` in the list (most recent)
    :raises IndexError: if no pools are found
    """
    return get_autorelease_pools(client)[-1]
