from typing import cast

from construct import Container

from rpcclient.clients.linux.structs import utsname
from rpcclient.core._types import SymbolT_co
from rpcclient.core.client import CoreClient
from rpcclient.core.symbol import Symbol
from rpcclient.utils import cached_async_method


class LinuxClient(CoreClient[SymbolT_co]):
    @cached_async_method
    async def get_uname(self) -> Container:
        async with self.safe_calloc(utsname.sizeof()) as uname:
            assert await self.symbols.uname(uname) == 0
            return await uname.parse(utsname)

    def symbol(self, symbol: int) -> SymbolT_co:
        return cast(SymbolT_co, Symbol(symbol, self))
