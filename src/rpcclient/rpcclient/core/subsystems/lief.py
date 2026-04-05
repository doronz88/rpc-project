from pathlib import PurePath
from typing import NamedTuple

import lief
import zyncio

from rpcclient.core._types import ClientBound, ClientT_co


class Symbol(NamedTuple):
    origin: object
    value: int


class Lief(ClientBound[ClientT_co]):
    """parse and patch executable files"""

    def __init__(self, client: ClientT_co) -> None:
        self._client = client

    @zyncio.zmethod
    async def parse(
        self, path: str | PurePath
    ) -> lief.COFF.Binary | lief.ELF.Binary | lief.MachO.Binary | lief.OAT.Binary | lief.PE.Binary | None:
        async with await self._client.fs.open.z(path, "r") as f:
            return lief.parse(await f.read.z())

    @zyncio.zmethod
    async def get_symbols(self, path: str | PurePath) -> dict[str | bytes, Symbol]:
        parsed = await self.parse.z(path)
        assert parsed is not None
        return {
            s.name: Symbol(
                origin=getattr(s, "origin", None),
                value=s.value,
            )
            for s in parsed.symbols
        }
