from collections import namedtuple
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic

import zyncio
from objc_types_decoder.decode import decode as decode_type
from objc_types_decoder.decode import decode_with_tail

from rpcclient.clients.darwin._types import DarwinSymbolT, DarwinSymbolT_co


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient


Property = namedtuple("Property", "name attributes")
PropertyAttributes = namedtuple("PropertyAttributes", "synthesize type_ list")


def convert_encoded_property_attributes(encoded) -> PropertyAttributes:
    conversions = {
        "R": lambda x: "readonly",
        "C": lambda x: "copy",
        "&": lambda x: "strong",
        "N": lambda x: "nonatomic",
        "G": lambda x: "getter=" + x[1:],
        "S": lambda x: "setter=" + x[1:],
        "d": lambda x: "dynamic",
        "W": lambda x: "weak",
        "P": lambda x: "<garbage-collected>",
        "t": lambda x: "encoding=" + x[1:],
    }

    type_, tail = decode_with_tail(encoded[1:])
    attributes = []
    synthesize = None
    for attr in filter(None, tail.lstrip(",").split(",")):
        if attr[0] in conversions:
            attributes.append(conversions[attr[0]](attr))
        elif attr[0] == "V":
            synthesize = attr[1:]

    return PropertyAttributes(type_=type_, synthesize=synthesize, list=attributes)


@dataclass
class Method(Generic[DarwinSymbolT_co]):
    name: str
    client: "BaseDarwinClient[DarwinSymbolT_co]" = field(compare=False)
    address: int = field(compare=False)
    imp: int = field(compare=False)
    type_: str = field(compare=False)
    return_type: str = field(compare=False)
    is_class: bool = field(compare=False)
    args_types: list = field(compare=False)

    @staticmethod
    def from_data(data: dict, client: "BaseDarwinClient[DarwinSymbolT]") -> "Method[DarwinSymbolT]":
        """
        Create Method object from raw data.
        :param data: Data as loaded from get_objectivec_symbol_data.m.
        :param rpcclient.darwin.client.DarwinClient client: Darwin client.
        """
        return Method(
            name=data["name"],
            client=client,
            address=client.symbol(data["address"]),
            imp=client.symbol(data["imp"]),
            type_=data["type"],
            return_type=decode_type(data["return_type"]),
            is_class=data["is_class"],
            args_types=list(map(decode_type, data["args_types"])),
        )

    def __zync_proxy__(self) -> DarwinSymbolT_co:
        return self.client.null

    @zyncio.zmethod
    async def set_implementation(self, new_imp: int) -> None:
        await self.client.symbols.method_setImplementation.z(self.address, new_imp)
        self.imp = self.client.symbol(new_imp)

    @zyncio.zmethod
    async def always_return(self, value: bool) -> None:
        """
        Patch the method to always return the given value.
        """
        # Exported from rpcserver binary
        ret_val = await self.client.symbols["get_true" if value else "get_false"].resolve()
        await self.set_implementation.z(ret_val)

    def __str__(self) -> str:
        if ":" in self.name:
            args_names = self.name.split(":")
            print(args_names, self.args_types[2:])
            name = " ".join(["{}:({})".format(*arg) for arg in zip(args_names, self.args_types[2:], strict=False)])
        else:
            name = self.name
        prefix = "+" if self.is_class else "-"
        return f"{prefix} {name}; // 0x{self.address:x} (returns: {self.return_type})\n"
