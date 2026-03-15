import plistlib
import struct
from pathlib import PurePath
from typing import TYPE_CHECKING, Generic

import lief
import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.consts import kSecCodeMagicEntitlement
from rpcclient.core.subsystems.lief import Lief
from rpcclient.exceptions import NoEntitlementsError


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient  # noqa: F401


class DarwinLief(Lief["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    @zyncio.zmethod
    async def get_entitlements(self, path: str | PurePath) -> dict:
        async with await self._client.fs.open.z(path, "r") as f:
            buf = await f.read.z()

        parsed = lief.parse(buf)

        if not isinstance(parsed, lief.MachO.Binary):
            raise TypeError(f"{str(path)!r} is not a Mach-O binary")

        code_signature = buf[
            parsed.code_signature.data_offset : parsed.code_signature.data_offset + parsed.code_signature.data_size
        ]

        ent_magic = struct.pack(">I", kSecCodeMagicEntitlement)
        ent_magic_offset = code_signature.find(ent_magic)

        if ent_magic_offset == -1:
            raise NoEntitlementsError()

        ent_buf = code_signature[ent_magic_offset + len(ent_magic) + 4 :]
        end_plist_magic = b"</plist>"
        ent_buf = ent_buf[: ent_buf.find(end_plist_magic) + len(end_plist_magic)]
        return plistlib.loads(ent_buf)
