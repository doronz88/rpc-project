from collections import namedtuple
from typing import TYPE_CHECKING

import lief
from parameter_decorators import path_to_str

Symbol = namedtuple("Symbol", "origin value")

if TYPE_CHECKING:
    from rpcclient.core.client import CoreClient


class Lief:
    """ " parse and patch executable files"""

    def __init__(self, client: "CoreClient"):
        self._client = client

    @path_to_str("path")
    def parse(self, path: str):
        with self._client.fs.open(path, "r") as f:
            return lief.parse(f.read())

    @path_to_str("path")
    def get_symbols(self, path: str) -> dict[str, Symbol]:
        result = {}
        parsed = self.parse(path)
        for s in parsed.symbols:
            result[s.name] = Symbol(origin=s.origin, value=s.value)
        return result
