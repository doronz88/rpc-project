import abc
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import zyncio
from osstatus.cache import ErrorCode, get_possible_error_codes

from rpcclient.clients.darwin.common import CfSerializable, CfSerializableAny, CfSerializableT
from rpcclient.core.client import RemoteCallArg
from rpcclient.core.symbol import RETVAL_BIT_COUNT, AbstractSymbol, AsyncSymbol, BaseSymbol, Symbol
from rpcclient.exceptions import UnrecognizedSelectorError
from rpcclient.utils import assert_cast, readonly


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient
    from rpcclient.clients.darwin.objective_c.objective_c_symbol import ObjectiveCSymbol
    from rpcclient.clients.darwin.subsystems.processes import Region


DarwinSymbolT_co = TypeVar("DarwinSymbolT_co", bound="BaseDarwinSymbol[Any]", covariant=True)
BaseDarwinSymbolT = TypeVar("BaseDarwinSymbolT", bound="BaseDarwinSymbol[Any]")


class AbstractDarwinSymbol(AbstractSymbol, Generic[DarwinSymbolT_co]):
    @property
    @abc.abstractmethod
    def _darwin_client(self) -> "BaseDarwinClient[DarwinSymbolT_co]": ...

    async def _objc_call(self, selector: str, *params, **kwargs) -> Any:
        """call an objc method on a given object"""
        client = self._darwin_client
        sel = await client.symbols.sel_getUid.z(selector)
        if not await client.symbols.objc_msgSend.z(self, await client.symbols.sel_getUid.z("respondsToSelector:"), sel):
            raise UnrecognizedSelectorError(f"unrecognized selector '{selector}' sent to class")

        return await client.symbols.objc_msgSend.z(self, sel, *params, **kwargs)

    @zyncio.zmethod
    async def objc_call(
        self, selector: str, *params: RemoteCallArg, va_list_index: int | None = None
    ) -> DarwinSymbolT_co:
        """call an objc method on a given object and return a symbol"""
        return await self._objc_call(selector, *params, va_list_index=va_list_index)

    @zyncio.zmethod
    async def objc_call_raw(self, selector: str, *params: RemoteCallArg, **kwargs) -> Any:
        """call an objc method on a given object and return a symbol"""
        return await self._objc_call(selector, *params, **kwargs, return_raw=True)

    @zyncio.zmethod
    async def py(
        self, typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = CfSerializableAny
    ) -> CfSerializableT:
        """get a python object from a core foundation one

        :param typ: Ensure that the returned Python object is of the given type.
        """
        return assert_cast(typ, await self._darwin_client.decode_cf.z(self) if self != 0 else None)

    @zyncio.zproperty
    async def region(self) -> "Region | None":
        """get corresponding region"""
        client = self._darwin_client
        proc = await client.processes.get_by_pid.z(await client.get_pid.z())
        for region in await proc.get_regions.z():
            if (self >= region.start) and (self <= region.end):
                return region

    async def get_cfdesc(self, typ: type[CfSerializableT] = CfSerializableAny) -> CfSerializableT:
        """
        Get output from CFCopyDescription()
        :return: CFCopyDescription()'s output as a string
        """
        if self == 0:
            return assert_cast(typ, None)
        return await (await self._darwin_client.symbols.CFCopyDescription.z(self)).py.z(typ)

    @zyncio.zproperty
    async def cfdesc(self) -> CfSerializable:
        """
        Get output from CFCopyDescription()
        :return: CFCopyDescription()'s output as a string
        """
        return await self.get_cfdesc()

    @property
    def objc_symbol(self) -> "ObjectiveCSymbol[DarwinSymbolT_co]":
        """
        Get an ObjectiveC symbol of the same address
        :return: Object representing the ObjectiveC symbol
        """
        return self._darwin_client.objc_symbol(self)

    @property
    def osstatus(self) -> list[ErrorCode] | None:
        """Get possible translation to given error code by querying osstatus"""
        return get_possible_error_codes(self)

    @property
    def stripped_value(self) -> DarwinSymbolT_co:
        """Remove PAC upper bits"""
        return self._darwin_client.symbol(self & 0xFFFFFFFFF)


class BaseDarwinSymbol(AbstractDarwinSymbol[BaseDarwinSymbolT], BaseSymbol, Generic[BaseDarwinSymbolT]):
    @readonly
    def _client(self) -> "BaseDarwinClient[BaseDarwinSymbolT]": ...

    def __init__(self, value: int, client: "BaseDarwinClient[BaseDarwinSymbolT]") -> None:
        self.retval_bit_count: int = RETVAL_BIT_COUNT
        self.is_retval_signed: bool = True
        self.item_size: int = 8
        BaseDarwinSymbol._client.set(self, client)
        self._offset: int = 0

    @property
    def _darwin_client(self) -> "BaseDarwinClient[BaseDarwinSymbolT]":
        return self._client


class DarwinSymbol(BaseDarwinSymbol["DarwinSymbol"], Symbol):
    pass


class AsyncDarwinSymbol(BaseDarwinSymbol["AsyncDarwinSymbol"], AsyncSymbol):
    pass
