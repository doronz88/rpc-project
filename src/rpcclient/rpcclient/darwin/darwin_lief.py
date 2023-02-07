import plistlib
import struct
from typing import Mapping

import lief
from parameter_decorators import path_to_str

from rpcclient.darwin.consts import kSecCodeMagicEntitlement
from rpcclient.exceptions import NoEntitlementsError
from rpcclient.lief import Lief


class DarwinLief(Lief):
    @path_to_str('path')
    def get_entitlements(self, path: str) -> Mapping:
        with self._client.fs.open(path, 'r') as f:
            buf = f.read()
        parsed = lief.parse(buf)
        code_signature = buf[parsed.code_signature.data_offset:
                             parsed.code_signature.data_offset + parsed.code_signature.data_size]

        ent_magic = struct.pack('>I', kSecCodeMagicEntitlement)
        ent_magic_offset = code_signature.find(ent_magic)

        if ent_magic_offset == -1:
            raise NoEntitlementsError()

        ent_buf = code_signature[ent_magic_offset + len(ent_magic) + 4:]
        end_plist_magic = b'</plist>'
        ent_buf = ent_buf[:ent_buf.find(end_plist_magic) + len(end_plist_magic)]
        return plistlib.loads(ent_buf)
