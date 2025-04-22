import re
from collections import UserList
from typing import List, Optional

from rpcclient.darwin.symbol import DarwinSymbol

POOL_BASE_MAGIC = '################  POOL BASE\n'
POOL_RE = re.compile(
    r'^[^\n]*#{2,}\s+POOL\s+(?P<name>\S+)'        # allow anything before the hashes
    r'(?P<body>.*?)(?=^[^\n]*#{2,}\s+POOL|\Z)',   # up to the next same‐pattern header
    re.DOTALL | re.MULTILINE
)
OBJ_ADDR = re.compile(
    r'\[0x[0-9A-Fa-f]+\]\s+'      # skip the address in the pool
    r'(?:0x)?([0-9A-Fa-f]+)'      # capture the address of the object
)
STDERR_FD = 2
SOCK_BUFFER_SIZE = 100 * 1024 * 1024  # 100MB


class AutoreleasePool(UserList[DarwinSymbol]):
    """
    A list-like container for `DarwinSymbol` objects representing one Objective-C autorelease pool.
    """

    def __init__(self, client, name: str, raw: str) -> None:
        """
        Initialize `AutoreleasePool` by parsing the raw pool dump.

        :param client:
        :param name: String uniquely naming this pool ("BASE" for the base pool and address for any other).
        :param raw: Raw text body of pool dump.
        """
        super().__init__()
        self._client = client
        self.name = name
        self._parse_pool(raw)

    def _parse_pool(self, raw: str) -> None:
        """
        Extract object addresses from raw dump and append DarwinSymbol instances.

        :param raw: Raw text body of pool dump.
        """
        raw_objs = OBJ_ADDR.findall(raw)
        for obj_hex in raw_objs:
            addr_int = int(obj_hex, 16)
            sym = self._client.symbol(addr_int)
            self.append(sym)

    def __repr__(self) -> str:
        """
        Return human-readable representation showing pool name and object count.

        :return: String representation of the pool
        """
        return f'<{self.__class__.__name__} {self.name} contains {len(self)} objects>'

    def __str__(self) -> str:
        """
        Return string representation showing pool name all of the objects inside.

        :return: String representation of the pool
        """
        output = f'{self.__class__.__name__} {self.name}:\n'

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
        Create the `NSAutoreleasePool` if not already present.
        """
        if self._pool is None:
            klass = self._client.symbols.objc_getClass('NSAutoreleasePool')
            self._pool = klass.objc_call('new')

    def drain(self) -> None:
        """
        Drain (release) the current autorelease pool if it exists, then clear it.
        """
        if self._pool is not None:
            self._pool.objc_call('drain')
            self._pool = None

    def _get_autorelease_pool(self) -> Optional[AutoreleasePool]:
        """
        Experimental: Locate current autorelease pool by comparing object addresses.

        Warning: Relies on unconfirmed implementation details of `NSAutoreleasePool`.

        :return: `AutoreleasePool` instance if found, else None
        """
        if self._pool is not None:
            start_addr = self._pool[1]
            name_hex = hex(start_addr)
            for pool in get_autorelease_pools(self._client):
                if pool.name == name_hex:
                    return pool
        return None


def get_autorelease_pools_str(client) -> str:
    """
    Get raw autorelease pool dump from stderr using `_objc_autoreleasePoolPrint`, handling known off-by-one bug.

    :param client:
    :return: Full raw text of all pools printed to stderr
    """
    # Because of a bug in the implementation of _objc_autoreleasePoolPrint
    # the last object in the autorelease pool will not show.
    # In order to amend that an empty pool is created and released.
    AutorelesePoolCtx(client).drain()
    with client.capture_fd(STDERR_FD, SOCK_BUFFER_SIZE) as cap:
        client.symbols._objc_autoreleasePoolPrint()
        data = cap.read()
    return data.decode('utf-8')


def get_autorelease_pools(client) -> List[AutoreleasePool]:
    """
    Get and parse all autorelease pools currently in the thread.

    :param client:
    :return: List of `AutoreleasePool` instances found in the dump
    """
    raw = POOL_BASE_MAGIC + get_autorelease_pools_str(client)
    pools: List[AutoreleasePool] = []
    for match in POOL_RE.finditer(raw):
        name = match.group('name')
        body = match.group('body')
        pools.append(AutoreleasePool(client, name, body))
    return pools


def get_current_autorelease_pool(client) -> AutoreleasePool:
    """
    Get the most recently created autorelease pool.

    :param client:
    :return: The last `AutoreleasePool` in the list (most recent)
    :raises IndexError: if no pools are found
    """
    return get_autorelease_pools(client)[-1]
