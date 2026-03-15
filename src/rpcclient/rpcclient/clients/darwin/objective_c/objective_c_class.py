from collections import namedtuple
from collections.abc import Coroutine
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, Literal, overload

import zyncio
from pygments import highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import ObjectiveCLexer

from rpcclient.clients.darwin._types import DarwinSymbolT, DarwinSymbolT_co
from rpcclient.clients.darwin.objective_c import objc
from rpcclient.core._types import ClientBound
from rpcclient.core.client import RemoteCallArg
from rpcclient.core.symbols_jar import SymbolsJar
from rpcclient.exceptions import GettingObjectiveCClassError


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient
    from rpcclient.clients.darwin.objective_c.objective_c_symbol import ObjectiveCSymbol
    from rpcclient.clients.darwin.symbol import AsyncDarwinSymbol, DarwinSymbol


Ivar = namedtuple("Ivar", "name type_ offset")


class Class(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Wrapper for ObjectiveC Class object.
    """

    def __init__(
        self,
        client: "BaseDarwinClient[DarwinSymbolT_co]",
        class_object: int = 0,
        class_data: dict | None = None,
        lazy: bool = False,
    ) -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client: Darwin client.
        :param rpcclient.darwin.objective_c_symbol.Symbol class_object:
        """
        self._client = client
        self._class_object: DarwinSymbolT_co = client.symbol(class_object)
        self.protocols = []
        self.ivars = []
        self.properties = []
        self.methods: list[objc.Method[DarwinSymbolT_co]] = []
        self.name: str = ""
        self.super = None
        if not lazy:
            if class_data is None:
                if not zyncio.is_sync(self):
                    raise TypeError("non-lazy initialization is not supported on async clients")
                self.reload()
            else:
                self._load_class_data(class_data)

    @staticmethod
    async def from_class_name(client: "BaseDarwinClient[DarwinSymbolT]", class_name: str) -> "Class[DarwinSymbolT]":
        """
        Create ObjectiveC Class from given class name.
        :param rpcclient.darwin.client.DarwinClient client: Darwin client.
        :param class_name: Class name.
        """
        class_object = await client.symbols.objc_getClass.z(class_name)
        if not class_object:
            raise GettingObjectiveCClassError()
        class_symbol = Class(client, class_object, lazy=True)
        await class_symbol.reload.z()
        if class_symbol.name != class_name:
            raise GettingObjectiveCClassError()
        return class_symbol

    @staticmethod
    def sanitize_name(name: str) -> str:
        """
        Sanitize python name to ObjectiveC name.
        """
        name = "_" + name[1:].replace("_", ":") if name.startswith("_") else name.replace("_", ":")
        return name

    @zyncio.zmethod
    async def reload(self) -> None:
        """
        Reload class object data.
        Should be used whenever the class layout changes (for example, during method swizzling)
        """
        objc_class = self._class_object if self._class_object else await self._client.symbols.objc_getClass.z(self.name)
        class_description = await self._client.showclass.z(objc_class)

        self.super = Class(self._client, class_description["super"], lazy=True) if class_description["super"] else None
        if self.super is not None:
            await self.super.reload.z()
        self.name = class_description["name"]
        self.protocols = class_description["protocols"]
        self.ivars = [
            Ivar(name=ivar["name"], type_=ivar["type"], offset=ivar["offset"]) for ivar in class_description["ivars"]
        ]
        self.properties = [
            objc.Property(name=prop["name"], attributes=objc.convert_encoded_property_attributes(prop["attributes"]))
            for prop in class_description["properties"]
        ]
        self.methods = [objc.Method.from_data(method, self._client) for method in class_description["methods"]]

    def show(self, dump_to: str | None = None) -> None:
        """
        Print to terminal the highlighted class description.
        :param dump_to: directory to dump.
        """
        formatted = str(self)
        print(highlight(formatted, ObjectiveCLexer(), TerminalTrueColorFormatter(style="native")))

        if dump_to is None:
            return
        (Path(dump_to) / f"{self.name}.m").expanduser().write_text(formatted)

    @zyncio.zmethod
    async def objc_call(self, sel: str, *args, **kwargs) -> DarwinSymbolT_co:
        """
        Invoke a selector on the given class object.
        :param sel: Selector name.
        :return: whatever the selector returned as a symbol.
        """
        return await self._class_object.objc_call.z(sel, *args, **kwargs)

    def get_method(self, name: str) -> objc.Method[DarwinSymbolT_co] | None:
        """
        Get a specific method implementation.
        :param name: Method name.
        :return: Method.
        """
        for method in self.methods:
            if method.name == name:
                return method

    def iter_supers(self):
        """
        Iterate over the super classes of the class.
        """
        sup = self.super
        while sup is not None:
            yield sup
            sup = sup.super

    def _load_class_data(self, data: dict) -> None:
        self._class_object = self._client.symbol(data["address"])
        self.super = Class(self._client, data["super"]) if data["super"] else None
        self.name = data["name"]
        self.protocols = data["protocols"]
        self.ivars = [Ivar(name=ivar["name"], type_=ivar["type"], offset=ivar["offset"]) for ivar in data["ivars"]]
        self.properties = data["properties"]
        self.methods = data["methods"]

    @property
    def symbols_jar(self: "Class[DarwinSymbolT_co]") -> SymbolsJar[DarwinSymbolT_co]:
        """Get a BaseSymbolsJar object for quick operations on all methods"""
        jar = SymbolsJar(self._client)

        for m in self.methods:
            jar[f"[{self.name} {m.name}]"] = m.address

        return jar

    @zyncio.zproperty
    async def bundle_path(self) -> Path:
        return Path(
            str(
                await (
                    await (
                        await (await self._client.symbols.objc_getClass.z("NSBundle")).objc_call.z(
                            "bundleForClass:", self._class_object
                        )
                    ).objc_call.z("bundlePath")
                ).py.z()
            )
        )

    def __dir__(self):
        result = set()

        for method in self.methods:
            if method.is_class:
                result.add(method.name.replace(":", "_"))

        for sup in self.iter_supers():
            for method in sup.methods:
                if method.is_class:
                    result.add(method.name.replace(":", "_"))

        result.update(list(super().__dir__()))
        return list(result)

    def __str__(self):
        protocol_buf = f"<{','.join(self.protocols)}>" if self.protocols else ""

        if self.super is not None:
            buf = f"@interface {self.name}: {self.super.name} {protocol_buf}\n"
        else:
            buf = f"@interface {self.name} {protocol_buf}\n"

        # Add ivars
        buf += "{\n"
        for ivar in self.ivars:
            buf += f"\t{ivar.type_} {ivar.name}; // 0x{ivar.offset:x}\n"
        buf += "}\n"

        # Add properties
        for prop in self.properties:
            buf += f"@property ({','.join(prop.attributes.list)}) {prop.attributes.type_} {prop.name};\n"

            if prop.attributes.synthesize is not None:
                buf += f"@synthesize {prop.name} = {prop.attributes.synthesize};\n"

        # Add methods
        for method in self.methods:
            buf += str(method)

        buf += "@end"
        return buf

    def __repr__(self):
        return f'<objC Class "{self.name}">'

    def __getitem__(self, item: str) -> "BoundObjectiveCMethod[DarwinSymbolT_co]":
        for method in self.methods:
            if method.name == item:
                if method.is_class:
                    return BoundObjectiveCMethod(self, item)
                else:
                    raise AttributeError(f"{self.name} class has an instance method named {item}, not a class method")

        for sup in self.iter_supers():
            for method in sup.methods:
                if method.name == item:
                    if method.is_class:
                        return BoundObjectiveCMethod(self, item)
                    else:
                        raise AttributeError(
                            f"{self.name} class has an instance method named {item}, not a class method"
                        )

        raise AttributeError(f"{self.name!r} class has no attribute {item!r}")

    def __getattr__(self, item: str):
        return self[self.sanitize_name(item)]


class BoundObjectiveCMethod(Generic[DarwinSymbolT_co]):
    def __init__(self, target: "Class[DarwinSymbolT_co] | ObjectiveCSymbol[DarwinSymbolT_co]", sel: str) -> None:
        self.target: Class[DarwinSymbolT_co] | ObjectiveCSymbol[DarwinSymbolT_co] = target
        self.sel: str = sel

    @overload
    def __call__(
        self: "BoundObjectiveCMethod[DarwinSymbol]",
        *args: RemoteCallArg,
        return_float64: Literal[False] = False,
        return_float32: Literal[False] = False,
        return_raw: Literal[False] = False,
        va_list_index: int | None = None,
    ) -> "DarwinSymbol": ...
    @overload
    def __call__(
        self: "BoundObjectiveCMethod[DarwinSymbol]",
        *args: "RemoteCallArg",
        return_float64: Literal[True],
        va_list_index: int | None = None,
    ) -> float: ...
    @overload
    def __call__(
        self: "BoundObjectiveCMethod[DarwinSymbol]",
        *args: "RemoteCallArg",
        return_float32: Literal[True],
        va_list_index: int | None = None,
    ) -> float: ...
    @overload
    def __call__(
        self: "BoundObjectiveCMethod[DarwinSymbol]",
        *args: "RemoteCallArg",
        return_raw: Literal[True],
        va_list_index: int | None = None,
    ) -> Any: ...
    @overload
    def __call__(
        self: "BoundObjectiveCMethod[DarwinSymbol]", *args: "RemoteCallArg", **kwargs
    ) -> "float | DarwinSymbol | Any": ...
    @overload
    async def __call__(
        self: "BoundObjectiveCMethod[AsyncDarwinSymbol]",
        *args: "RemoteCallArg",
        return_float64: Literal[False] = False,
        return_float32: Literal[False] = False,
        return_raw: Literal[False] = False,
        va_list_index: int | None = None,
    ) -> "AsyncDarwinSymbol": ...
    @overload
    async def __call__(
        self: "BoundObjectiveCMethod[AsyncDarwinSymbol]",
        *args: "RemoteCallArg",
        return_float64: Literal[True],
        va_list_index: int | None = None,
    ) -> float: ...
    @overload
    async def __call__(
        self: "BoundObjectiveCMethod[AsyncDarwinSymbol]",
        *args: "RemoteCallArg",
        return_float32: Literal[True],
        va_list_index: int | None = None,
    ) -> float: ...
    @overload
    async def __call__(
        self: "BoundObjectiveCMethod[AsyncDarwinSymbol]",
        *args: "RemoteCallArg",
        return_raw: Literal[True],
        va_list_index: int | None = None,
    ) -> Any: ...
    @overload
    async def __call__(
        self: "BoundObjectiveCMethod[AsyncDarwinSymbol]", *args: "RemoteCallArg", **kwargs
    ) -> "float | AsyncDarwinSymbol | Any": ...
    def __call__(
        self, *args: "RemoteCallArg", **kwargs
    ) -> "float | DarwinSymbol | Any | Coroutine[Any, Any, float | AsyncDarwinSymbol | Any]":
        if zyncio.is_sync(self.target):
            return self.target.objc_call(self.sel, *args, **kwargs)
        return self.target.objc_call.z(self.sel, *args, **kwargs)
