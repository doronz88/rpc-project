import abc
import ctypes
import os
import struct
from collections.abc import Coroutine, Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast, final, overload
from typing_extensions import Self

from capstone import CS_ARCH_ARM64, CS_ARCH_X86, CS_MODE_64, CS_MODE_LITTLE_ENDIAN, Cs, CsInsn

from rpcclient.core.structs.generic import Dl_info
from rpcclient.protos.rpc_pb2 import ARCH_ARM64
from rpcclient.utils import readonly


if TYPE_CHECKING:
    from construct import Construct, Container, ParsedType

    from rpcclient.core.client import CoreClient, RemoteCallArg


ADDRESS_SIZE_TO_STRUCT_FORMAT = {1: "B", 2: "H", 4: "I", 8: "Q"}
RETVAL_BIT_COUNT = 64


SymbolT_co = TypeVar("SymbolT_co", bound="Symbol", covariant=True)


class AbstractSymbol(int, abc.ABC):
    """Abstract wrapper for a remote symbol object"""

    @final
    def __new__(cls, value: int, *args, **kwargs) -> Self:
        if not isinstance(value, int):
            raise TypeError(f"expected int, got {type(value).__qualname__}")

        value &= 0xFFFFFFFFFFFFFFFF

        return super().__new__(cls, value)

    @abc.abstractmethod
    def _symbol_from_value(self, value: int) -> Self:
        """
        Returns the given value as a symbol.
        The symbol's type can change depending on the value and/or the symbol's state.

        :param value: Symbol address
        :return: Symbol object.
        :rtype: Symbol
        """

    @contextmanager
    def change_item_size(self, new_item_size: int) -> Generator[None]:
        """
        Temporarily change item size
        :param new_item_size: Temporary item size
        """
        save_item_size = self.item_size
        self.item_size = new_item_size
        try:
            yield
        finally:
            self.item_size = save_item_size

    @abc.abstractmethod
    async def peek(self, count: int, offset: int = 0) -> bytes: ...

    @abc.abstractmethod
    async def poke(self, buf: bytes, offset: int = 0) -> Any: ...

    @abc.abstractmethod
    async def peek_str(self, encoding="utf-8") -> str:
        """peek string at given address"""

    def close(self) -> None:
        """Construct compliance."""
        pass

    def seek(self, offset: int, whence: int) -> None:
        """Construct compliance."""
        if whence == os.SEEK_CUR:
            self._offset += offset
        elif whence == os.SEEK_SET:
            self._offset = offset - self
        else:
            raise OSError("Unsupported whence")

    async def read(self, count: int) -> bytes:
        """Construct compliance."""
        val = await (self + self._offset).peek(count)
        self._offset += count
        return val

    async def write(self, buf: bytes) -> None:
        """Construct compliance."""
        val = await (self + self._offset).poke(buf)
        self._offset += len(buf)
        return val

    def tell(self) -> Self:
        """Construct compliance."""
        return self + self._offset

    @property
    @abc.abstractmethod
    def arch(self) -> object: ...

    async def disass(self, size=40) -> list[CsInsn]:
        """peek disassembled lines of 'size' bytes"""
        cs = (
            Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
            if self.arch == ARCH_ARM64
            # assume x86_64 by default
            else Cs(CS_ARCH_X86, CS_MODE_LITTLE_ENDIAN | CS_MODE_64)
        )

        return list(cs.disasm(await self.peek(size), self))

    @property
    def c_int64(self) -> int:
        """cast to c_int64"""
        return ctypes.c_int64(self).value

    @property
    def c_uint64(self) -> int:
        """cast to c_uint64"""
        return ctypes.c_uint64(self).value

    @property
    def c_int32(self) -> int:
        """cast to c_int32"""
        return ctypes.c_int32(self).value

    @property
    def c_uint32(self) -> int:
        """cast to c_uint32"""
        return ctypes.c_uint32(self).value

    @property
    def c_int16(self) -> int:
        """cast to c_int16"""
        return ctypes.c_int16(self).value

    @property
    def c_uint16(self) -> int:
        """cast to c_uint16"""
        return ctypes.c_uint16(self).value

    @property
    def c_bool(self) -> bool:
        """cast to c_bool"""
        return ctypes.c_bool(self).value

    @abc.abstractmethod
    async def get_dl_info(self) -> "Container": ...

    async def dl_info(self) -> "Container":
        return await self.get_dl_info()

    async def name(self) -> str:
        return (await self.get_dl_info()).dli_sname

    async def filename(self) -> str:
        return (await self.get_dl_info()).dli_fname

    @property
    @abc.abstractmethod
    def endianness(self) -> str: ...

    async def getindex(self, index: int, *indices: int) -> Self:
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        new_symbol = self._symbol_from_value(
            struct.unpack(self.endianness + fmt, await self.peek(self.item_size, offset=index * self.item_size))[0]
        )
        if indices:
            return await new_symbol.getindex(*indices)
        return new_symbol

    async def setindex(self, index: int, value) -> None:
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        value = struct.pack(self.endianness + fmt, int(value))
        await self.poke(value, offset=index * self.item_size)

    def __getitem__(self, item: int) -> Coroutine[Any, Any, Self]:
        """Read a remote item: ``await sym[i]`` (awaitable alias for ``getindex``)."""
        return self.getindex(item)

    def __setitem__(self, item: int, value) -> None:
        raise TypeError(
            "item assignment can't be awaited; use `await sym.setindex(index, value)` instead of `sym[index] = value`"
        )

    async def parse(self, struct: "Construct[ParsedType, Any]") -> "ParsedType":
        return struct.parse(await self.peek(struct.sizeof()))

    def __add__(self, other) -> Self:
        try:
            return self._symbol_from_value(int(self) + other)
        except TypeError:
            return int(self) + other

    def __radd__(self, other) -> Self:
        return self.__add__(other)

    def __sub__(self, other) -> Self:
        try:
            return self._symbol_from_value(int(self) - other)
        except TypeError:
            return int(self) - other

    def __rsub__(self, other) -> Self:
        try:
            return self._symbol_from_value(other - int(self))
        except TypeError:
            return other - int(self)

    def __mul__(self, other) -> Self:
        try:
            return self._symbol_from_value(int(self) * other)
        except TypeError:
            return int(self) * other

    def __rmul__(self, other) -> Self:
        return self.__mul__(other)

    def __truediv__(self, other) -> Self:
        return self._symbol_from_value(int(self) / other)

    def __floordiv__(self, other) -> Self:
        return self._symbol_from_value(int(self) // other)

    def __mod__(self, other) -> Self:
        return self._symbol_from_value(int(self) % other)

    def __and__(self, other) -> Self:
        return self._symbol_from_value(int(self) & other)

    def __or__(self, other) -> Self:
        return self._symbol_from_value(int(self) | other)

    def __xor__(self, other) -> Self:
        return self._symbol_from_value(int(self) ^ other)

    def __repr__(self) -> str:
        return f"<{type(self).__name__}: {hex(self)}>"

    def __str__(self) -> str:
        return hex(self)


class Symbol(AbstractSymbol):
    """wrapper for a remote symbol object"""

    @readonly
    def _client(self) -> "CoreClient[Self]": ...

    def __init__(self, value: int, client: "CoreClient[Self]") -> None:
        """
        Create a Symbol object.
        :param value: Symbol address.
        :param client: client.
        :return: Symbol object.
        :rtype: Symbol
        """
        self.retval_bit_count: int = RETVAL_BIT_COUNT
        self.is_retval_signed: bool = True
        self.item_size: int = 8

        # private members
        __class__._client.set(self, client)
        self._offset: int = 0

    def _symbol_from_value(self, value: int) -> Self:
        """
        Returns the given value as a symbol.
        The symbol's type can change depending on the value and/or the symbol's state.

        :param value: Symbol address
        :return: Symbol object.
        :rtype: Symbol
        """
        return type(self)(value, cast("CoreClient", self._client))

    async def peek(self, count: int, offset: int = 0) -> bytes:
        return await self._client.peek(self + offset, count)

    async def poke(self, buf: bytes, offset: int = 0) -> Any:
        return await self._client.poke(self + offset, buf)

    async def peek_str(self, encoding="utf-8") -> str:
        """peek string at given address"""
        str_len = await self._client.symbols.strlen(self)
        return (await self.peek(str_len)).decode(encoding)

    @property
    def arch(self) -> object:
        return self._client.arch

    async def get_dl_info(self) -> "Container":
        dl_info = Dl_info(self._client)
        sizeof = dl_info.sizeof()
        async with self._client.safe_malloc(sizeof) as info:
            if await self._client.symbols.dladdr(self, info) == 0:
                await self._client.raise_errno_exception(f"failed to extract info for: {self}")
            return dl_info.parse(await info.read(sizeof))

    @property
    def endianness(self) -> str:
        return self._client._endianness

    async def resolve(self) -> Self:
        """Return this symbol unchanged.

        This method exists to allow calling `resolve()` on an object that may be either a symbol or a `LazySymbol`.
        """
        return self

    @overload
    async def call(
        self,
        *args: "RemoteCallArg",
        return_float64: Literal[False] = False,
        return_float32: Literal[False] = False,
        return_raw: Literal[False] = False,
        va_list_index: int | None = None,
    ) -> Self: ...
    @overload
    async def call(
        self, *args: "RemoteCallArg", return_float64: Literal[True], va_list_index: int | None = None
    ) -> float: ...
    @overload
    async def call(
        self, *args: "RemoteCallArg", return_float32: Literal[True], va_list_index: int | None = None
    ) -> float: ...
    @overload
    async def call(
        self, *args: "RemoteCallArg", return_raw: Literal[True], va_list_index: int | None = None
    ) -> Any: ...
    @overload
    async def call(self, *args: "RemoteCallArg", **kwargs) -> "float | Self | Any": ...
    async def call(self, *args: "RemoteCallArg", **kwargs) -> "float | Self | Any":
        """Call this symbol as a function pointer."""
        return await self._client.call(self, args, **kwargs)

    __call__ = call
