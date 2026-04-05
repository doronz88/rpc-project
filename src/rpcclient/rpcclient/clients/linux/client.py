import zyncio
from construct import Container

from rpcclient.clients.linux.structs import utsname
from rpcclient.core._types import SymbolT_co
from rpcclient.core.client import AsyncCoreClient, BaseCoreClient, CoreClient
from rpcclient.core.symbol import Symbol
from rpcclient.utils import cached_async_method


class BaseLinuxClient(BaseCoreClient[SymbolT_co]):
    @zyncio.zmethod
    @cached_async_method
    async def get_uname(self) -> Container:
        async with self.safe_calloc.z(utsname.sizeof()) as uname:
            assert await self.symbols.uname.z(uname) == 0
            return await uname.parse.z(utsname)


class LinuxClient(BaseLinuxClient[Symbol], CoreClient):
    pass


class AsyncLinuxClient(BaseLinuxClient[Symbol], AsyncCoreClient):
    pass
