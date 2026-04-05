from collections.abc import Coroutine
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, overload

import zyncio
from construct import Container
from pygments import highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import ObjectiveCLexer

from rpcclient.clients.darwin._types import AsyncDarwinSymbolT_co, DarwinSymbolT, DarwinSymbolT_co, SyncDarwinSymbolT_co
from rpcclient.clients.darwin.objective_c import objc
from rpcclient.clients.darwin.objective_c.objc import Method
from rpcclient.clients.darwin.objective_c.objective_c_class import BoundObjectiveCMethod, Class
from rpcclient.clients.darwin.symbol import BaseDarwinSymbol, DarwinSymbol
from rpcclient.core._types import ClientBound
from rpcclient.core.client import RemoteCallArg
from rpcclient.core.symbol import AbstractSymbol
from rpcclient.core.symbols_jar import SymbolsJar
from rpcclient.exceptions import RpcClientException


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient


class SettingIvarError(RpcClientException):
    """Raise when trying to set an Ivar too early or when the Ivar doesn't exist."""

    pass


@dataclass
class Ivar(Generic[DarwinSymbolT_co]):
    name: str
    value: DarwinSymbolT_co
    type_: str
    offset: int


class ObjectiveCSymbol(AbstractSymbol, ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Wrapper object for an objective-c symbol.
    Allowing easier access to its properties, methods and ivars.
    """

    _attrs = frozenset({"__zync_mode__", "_client", "_sym", "class_", "ivars", "methods", "properties"})

    __zync_mode__: None = None  # Prevent RecursionError due to __getattr__

    def __init__(self, value: int, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        """
        Create an ObjectiveCSymbol object.
        :param value: Symbol address.
        :param rpcclient.darwin.client.Client client: client.
        :return: ObjectiveCSymbol object.
        :rtype: ObjectiveCSymbol
        """
        self._client = client
        self._sym: DarwinSymbolT_co = client.symbol(value)
        self.ivars: list[Ivar[DarwinSymbolT_co]] = []
        self.methods: list[Method[DarwinSymbolT_co]] = []
        self.properties: list[objc.Property] = []
        self.class_: Class[DarwinSymbolT_co] | None = None

        if zyncio.is_sync(self):
            self.reload()

    def _symbol_from_value(self, value: int) -> DarwinSymbolT_co:
        """
        Returns the gives value as as a BaseDarwinSymbol.
        This static behvaior is needed, as no value can definitely be a valid objc object.
        Because treating a value as an objc address may lead to a segmentation fault, it is safer to treat it as a more general symbol.

        :param value: Symbol address
        :return: BaseDarwinSymbol object.
        :rtype: BaseDarwinSymbol
        """
        return self._client.symbol(value)

    @zyncio.zmethod
    async def peek(self, count: int, offset: int = 0) -> bytes:
        return await self._sym.peek.z(count, offset)

    @zyncio.zmethod
    async def poke(self, buf: bytes, offset: int = 0) -> Any:
        return await self._sym.poke.z(buf, offset)

    @zyncio.zmethod
    async def peek_str(self, encoding="utf-8") -> str:
        """peek string at given address"""
        return await self._sym.peek_str.z(encoding=encoding)

    @property
    def arch(self) -> object:
        return self._client.arch

    @property
    def endianness(self) -> str:
        return self._client._endianness

    @zyncio.zmethod
    async def get_dl_info(self) -> Container:
        return await self._sym.get_dl_info.z()

    @zyncio.zmethod
    async def reload(self) -> None:
        """
        Reload object's in-memory layout.
        """
        object_data = await self._client.showobject.z(self)

        ivars_list = [
            Ivar(name=ivar["name"], type_=ivar["type"], offset=ivar["offset"], value=self._client.symbol(ivar["value"]))
            for ivar in object_data["ivars"]
        ]
        methods_list = [objc.Method.from_data(method, self._client) for method in object_data["methods"]]
        properties_list = [
            objc.Property(name=prop["name"], attributes=objc.convert_encoded_property_attributes(prop["attributes"]))
            for prop in object_data["properties"]
        ]

        class_object = self._client.symbol(object_data["class_address"])
        class_wrapper = Class(self._client, class_object, lazy=True)
        await class_wrapper.reload.z()

        self.ivars = ivars_list
        self.methods = methods_list
        self.properties = properties_list
        self.class_ = class_wrapper

    def show(self, dump_to: str | None = None, recursive: bool = False) -> None:
        """
        Print to terminal the highlighted class description.
        :param dump_to: directory to dump.
        :param recursive: Show methods of super classes.
        """
        if self.class_ is None:
            raise ValueError("Must call reload() before calling show() in async mode.")

        formatted = self._to_str(recursive)
        print(highlight(formatted, ObjectiveCLexer(), TerminalTrueColorFormatter(style="native")))

        if dump_to is None:
            return
        (Path(dump_to) / f"{self.class_.name}.m").expanduser().write_text(formatted)

    @zyncio.zmethod
    async def objc_call(self, selector: str, *params, **kwargs) -> Any:
        """
        Make objc_call() from self return ObjectiveCSymbol when it's an objc symbol.
        :param selector: Selector to execute.
        :param params: Additional parameters.
        :return: ObjectiveCSymbol when return type is an objc symbol.
        """
        symbol = await self._sym.objc_call.z(selector, *params, **kwargs)
        try:
            is_objc_type = self.get_method(selector).return_type == "id"
        except AttributeError:
            is_objc_type = False
        return symbol.objc_symbol if is_objc_type else symbol

    def get_method(self, name: str) -> Method[DarwinSymbolT_co]:
        for method in self.methods:
            if method.name == name:
                return method
        raise AttributeError(f'Method "{name}" does not exist')

    async def set_ivar(self: "ObjectiveCSymbol[DarwinSymbolT]", name: str, value: DarwinSymbolT) -> None:
        try:
            ivars = self.ivars
            assert self.class_ is not None
            class_name = self.class_.name
        except AttributeError as e:
            raise SettingIvarError from e

        for i, ivar in enumerate(ivars):
            if ivar.name == name:
                size = self.item_size
                if i < len(self.ivars) - 1:
                    size = ivars[i + 1].offset - ivar.offset
                with self.change_item_size(size):
                    await self.setindex(ivar.offset // size, value)
                    ivar.value = value
                return

        raise SettingIvarError(f"Ivar {name!r} does not exist in {class_name!r}")

    def _to_str(self, recursive: bool = False) -> str:
        if self.class_ is None:
            return f"<{type(self).__name__} {hex(self)} (not loaded)>"

        protocols_buf = f"<{','.join(self.class_.protocols)}>" if self.class_.protocols else ""

        if self.class_.super is not None:
            buf = f"@interface {self.class_.name}: {self.class_.super.name} {protocols_buf}\n"
        else:
            buf = f"@interface {self.class_.name} {protocols_buf}\n"

        # Add ivars
        buf += "{\n"
        for ivar in self.ivars:
            buf += f"\t{ivar.type_} {ivar.name} = 0x{int(ivar.value):x}; // 0x{ivar.offset:x}\n"
        buf += "}\n"

        # Add properties
        for prop in self.properties:
            attrs = prop.attributes
            buf += f"@property ({','.join(attrs.list)}) {prop.attributes.type_} {prop.name};\n"

            if attrs.synthesize is not None:
                buf += f"@synthesize {prop.name} = {attrs.synthesize};\n"

        # Add methods
        methods = self.methods.copy()

        # Add super methods.
        if recursive:
            for sup in self.class_.iter_supers():
                for method in filter(lambda m: m not in methods, sup.methods):
                    methods.append(method)

        # Print class methods first.
        methods.sort(key=lambda m: not m.is_class)

        for method in methods:
            buf += str(method)

        buf += "@end"
        return buf

    @property
    def symbols_jar(self) -> SymbolsJar[DarwinSymbolT_co]:
        """Get a BaseSymbolsJar object for quick operations on all methods"""
        jar = SymbolsJar(self._client)

        for m in self.methods:
            jar[m.name] = m.address

        return jar

    def __dir__(self):
        result = set()

        for ivar in self.ivars:
            result.add(ivar.name)

        for method in self.methods:
            result.add(method.name.replace(":", "_"))

        if self.class_ is not None:
            for sup in self.class_.iter_supers():
                for method in sup.methods:
                    result.add(method.name.replace(":", "_"))

        result.update(list(super().__dir__()))
        return list(result)

    @zyncio.zmethod
    async def get(
        self, name: str
    ) -> "ObjectiveCSymbol[DarwinSymbolT_co] | DarwinSymbolT_co | Any | BoundObjectiveCMethod[DarwinSymbolT_co]":
        if self.class_ is None:
            await self.reload.z()
            assert self.class_ is not None

        # Ivars
        for ivar in self.ivars:
            if ivar.name == name:
                if await self._client.is_objc_type.z(ivar.value):
                    return ivar.value.objc_symbol
                return ivar.value

        # Properties
        for prop in self.properties:
            if prop.name == name:
                return await self.objc_call.z(name)

        # Methods
        for method in self.methods:
            if method.name == name:
                return (
                    BoundObjectiveCMethod(self.class_, name) if method.is_class else BoundObjectiveCMethod(self, name)
                )

        for sup in self.class_.iter_supers():
            for method in sup.methods:
                if method.name == name:
                    return (
                        BoundObjectiveCMethod(self.class_, name)
                        if method.is_class
                        else BoundObjectiveCMethod(self, name)
                    )

        raise AttributeError(f"{self.class_.name!r} has no attribute {name!r}")

    @overload
    def __getitem__(self: "ObjectiveCSymbol[DarwinSymbol]", item: int) -> DarwinSymbol: ...
    @overload
    def __getitem__(
        self: "ObjectiveCSymbol[DarwinSymbol]", item: str
    ) -> "DarwinSymbol | ObjectiveCSymbol[DarwinSymbol] | Any | BoundObjectiveCMethod[DarwinSymbol]": ...
    def __getitem__(self: "ObjectiveCSymbol[DarwinSymbol]", item: int | str) -> object:
        if not isinstance(self._sym, DarwinSymbol):
            raise TypeError(f"indexing on {type(self).__name__} is only supported in sync mode")

        if isinstance(item, int):
            return self._sym[item]

        return self.get(item)

    def __getattr__(
        self: "ObjectiveCSymbol[DarwinSymbol]", item: str
    ) -> "DarwinSymbol | ObjectiveCSymbol[DarwinSymbol] | Any | BoundObjectiveCMethod[DarwinSymbol]":
        if not isinstance(self._sym, DarwinSymbol):
            raise TypeError(f"arbitrary attribute lookup on {type(self).__name__} is only supported in sync mode")

        if self.class_ is None:
            self.reload()
            assert self.class_ is not None
        return self[self.class_.sanitize_name(item)]

    @overload
    def __setitem__(self: "ObjectiveCSymbol[DarwinSymbolT]", key: str, value: DarwinSymbolT) -> None: ...
    @overload
    def __setitem__(self: "ObjectiveCSymbol[DarwinSymbol]", key: int | str, value: DarwinSymbol) -> None: ...
    def __setitem__(self: "ObjectiveCSymbol[DarwinSymbolT]", key: int | str, value: DarwinSymbolT) -> None:
        if not isinstance(self._sym, DarwinSymbol):
            raise TypeError(f"indexing on {type(self).__name__} is only supported in sync mode")

        if isinstance(key, int):
            self._sym[key] = value
        else:
            with suppress(SettingIvarError):
                zyncio.run_sync(self.set_ivar(key, value))

    def __setattr__(self: "ObjectiveCSymbol[DarwinSymbol]", key: str, value: DarwinSymbol) -> None:
        if key in self._attrs:
            return object.__setattr__(self, key, value)

        if self.class_ is None:
            self.reload()
            assert self.class_ is not None

        if not isinstance(self._sym, DarwinSymbol):
            raise TypeError(f"setting Ivars on {type(self).__name__} via __setattr__ is only supported in sync mode")

        with suppress(AttributeError):
            key = self.class_.sanitize_name(key)
        try:
            zyncio.run_sync(self.set_ivar(key, value))
        except SettingIvarError:
            super().__setattr__(key, value)

    def __str__(self):
        return self._to_str(False)

    def __repr__(self) -> str:
        class_name = self.class_.name if self.class_ is not None else "<not loaded>"
        return f"<{self.__class__.__name__} 0x{int(self):x} Class: {class_name}>"

    async def call(self, *args: RemoteCallArg) -> DarwinSymbolT_co:
        return await self._sym.call(*args)

    @overload
    def __call__(self: "ObjectiveCSymbol[SyncDarwinSymbolT_co]", *args: RemoteCallArg) -> SyncDarwinSymbolT_co: ...
    @overload
    async def __call__(
        self: "ObjectiveCSymbol[AsyncDarwinSymbolT_co]", *args: RemoteCallArg
    ) -> AsyncDarwinSymbolT_co: ...
    def __call__(self, *args: RemoteCallArg) -> BaseDarwinSymbol | Coroutine[Any, Any, BaseDarwinSymbol]:
        if zyncio.is_sync(self):
            return zyncio.run_sync(self.call(*args))
        return self.call(*args)
