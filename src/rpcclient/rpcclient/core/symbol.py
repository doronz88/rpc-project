import abc
import ctypes
import os
import struct
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast, final, overload
from typing_extensions import Self

import zyncio
from capstone import CS_ARCH_ARM64, CS_ARCH_X86, CS_MODE_64, CS_MODE_LITTLE_ENDIAN, Cs, CsInsn

from rpcclient.core.structs.generic import Dl_info
from rpcclient.protos.rpc_pb2 import ARCH_ARM64
from rpcclient.utils import readonly


if TYPE_CHECKING:
    from construct import Construct, Container, ParsedType

    from rpcclient.core.client import BaseCoreClient, RemoteCallArg


ADDRESS_SIZE_TO_STRUCT_FORMAT = {1: "B", 2: "H", 4: "I", 8: "Q"}
RETVAL_BIT_COUNT = 64


SymbolT_co = TypeVar("SymbolT_co", bound="BaseSymbol", covariant=True)


# `call` is defined here for type checking reasons.
# If it was defined in `BaseSymbol`, type checkers would
# assume that returned symbols are always `BaseSymbol`, even
# when called on a subclass (i.e. `AsyncSymbol(...).call()` would
# be assumed to be of type `BaseSymbol` instead of `AsyncSymbol`).
@overload
async def call(
    self: SymbolT_co,
    *args: "RemoteCallArg",
    return_float64: Literal[False] = False,
    return_float32: Literal[False] = False,
    return_raw: Literal[False] = False,
    va_list_index: int | None = None,
) -> SymbolT_co: ...
@overload
async def call(
    self: "BaseSymbol", *args: "RemoteCallArg", return_float64: Literal[True], va_list_index: int | None = None
) -> float: ...
@overload
async def call(
    self: "BaseSymbol", *args: "RemoteCallArg", return_float32: Literal[True], va_list_index: int | None = None
) -> float: ...
@overload
async def call(
    self: "BaseSymbol", *args: "RemoteCallArg", return_raw: Literal[True], va_list_index: int | None = None
) -> Any: ...
@overload
async def call(self: SymbolT_co, *args: "RemoteCallArg", **kwargs) -> float | SymbolT_co | Any: ...
async def call(self: SymbolT_co, *args: "RemoteCallArg", **kwargs) -> float | SymbolT_co | Any:
    """Call this symbol as a function pointer."""
    return await self._client.call.z(self, args, **kwargs)


call.__qualname__ = "BaseSymbol.call"


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

    @zyncio.zmethod
    @abc.abstractmethod
    async def peek(self, count: int, offset: int = 0) -> bytes: ...

    @zyncio.zmethod
    @abc.abstractmethod
    async def poke(self, buf: bytes, offset: int = 0) -> Any: ...

    @zyncio.zmethod
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

    @zyncio.zmethod
    async def read(self, count: int) -> bytes:
        """Construct compliance."""
        val = await (self + self._offset).peek.z(count)
        self._offset += count
        return val

    @zyncio.zmethod
    async def write(self, buf: bytes) -> None:
        """Construct compliance."""
        val = await (self + self._offset).poke.z(buf)
        self._offset += len(buf)
        return val

    def tell(self) -> Self:
        """Construct compliance."""
        return self + self._offset

    @property
    @abc.abstractmethod
    def arch(self) -> object: ...

    @zyncio.zmethod
    async def disass(self, size=40) -> list[CsInsn]:
        """peek disassembled lines of 'size' bytes"""
        cs = (
            Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
            if self.arch == ARCH_ARM64
            # assume x86_64 by default
            else Cs(CS_ARCH_X86, CS_MODE_LITTLE_ENDIAN | CS_MODE_64)
        )

        return list(cs.disasm(await self.peek.z(size), self))

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

    @zyncio.zmethod
    @abc.abstractmethod
    async def get_dl_info(self) -> "Container": ...

    @zyncio.zproperty
    async def dl_info(self) -> "Container":
        return await self.get_dl_info.z()

    @zyncio.zproperty
    async def name(self) -> str:
        return (await (self).get_dl_info.z()).dli_sname

    @zyncio.zproperty
    async def filename(self) -> str:
        return (await (self).get_dl_info.z()).dli_fname

    @property
    @abc.abstractmethod
    def endianness(self) -> str: ...

    async def getindex(self, index: int, *indices: int) -> Self:
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        new_symbol = self._symbol_from_value(
            struct.unpack(self.endianness + fmt, await self.peek.z(self.item_size, offset=index * self.item_size))[0]
        )
        if indices:
            return await new_symbol.getindex(*indices)
        return new_symbol

    async def setindex(self, index: int, value) -> None:
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        value = struct.pack(self.endianness + fmt, int(value))
        await self.poke.z(value, offset=index * self.item_size)

    @zyncio.zmethod
    async def parse(self, struct: "Construct[ParsedType, Any]") -> "ParsedType":
        return struct.parse(await self.peek.z(struct.sizeof()))

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


class BaseSymbol(AbstractSymbol, zyncio.ZyncBase):
    """wrapper for a remote symbol object"""

    @readonly
    def _client(self) -> "BaseCoreClient[Self]": ...

    def __init__(self, value: int, client: "BaseCoreClient[Self]") -> None:
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
        return type(self)(value, cast("BaseCoreClient", self._client))

    @zyncio.zmethod
    async def peek(self, count: int, offset: int = 0) -> bytes:
        return await self._client.peek.z(self + offset, count)

    @zyncio.zmethod
    async def poke(self, buf: bytes, offset: int = 0) -> Any:
        return await self._client.poke.z(self + offset, buf)

    @zyncio.zmethod
    async def peek_str(self, encoding="utf-8") -> str:
        """peek string at given address"""
        str_len = await self._client.symbols.strlen.z(self)
        return (await self.peek.z(str_len)).decode(encoding)

    @property
    def arch(self) -> object:
        return self._client.arch

    @zyncio.zmethod
    async def get_dl_info(self) -> "Container":
        dl_info = Dl_info(self._client)
        sizeof = dl_info.sizeof()
        async with self._client.safe_malloc.z(sizeof) as info:
            if await self._client.symbols.dladdr.z(self, info) == 0:
                await self._client.raise_errno_exception.z(f"failed to extract info for: {self}")
            return dl_info.parse(await info.read.z(sizeof))

    @property
    def endianness(self) -> str:
        return self._client._endianness

    async def resolve(self) -> Self:
        """Return this symbol unchanged.

        This method exists to allow calling `resolve()` on an object that may be either a symbol or a `LazySymbol`.
        """
        return self

    call = call
    """Always-async version of __call__, for writing zyncio interfaces."""

    z = call
    """Alias for `call`, for parity with other zyncio-callables."""


class Symbol(zyncio.SyncMixin, BaseSymbol):
    __call__ = zyncio.make_sync(call)

    def __getitem__(self, item: int) -> Self:
        return zyncio.run_sync(self.getindex(item))

    def __setitem__(self, item: int, value) -> None:
        zyncio.run_sync(self.setindex(item, value))


class AsyncSymbol(zyncio.AsyncMixin, BaseSymbol):
    __call__ = call
