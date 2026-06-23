from typing import TYPE_CHECKING, Any
from typing_extensions import Self

from osstatus.cache import ErrorCode, get_possible_error_codes

from rpcclient.clients.darwin.common import CfSerializable, CfSerializableAny, CfSerializableT
from rpcclient.core.client import RemoteCallArg
from rpcclient.core.symbol import AbstractSymbol, Symbol
from rpcclient.exceptions import UnrecognizedSelectorError
from rpcclient.utils import assert_cast, readonly


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient
    from rpcclient.clients.darwin.objective_c.objective_c_symbol import ObjectiveCSymbol
    from rpcclient.clients.darwin.subsystems.processes import Region


class AbstractDarwinSymbol(AbstractSymbol):
    @readonly
    def _client(self) -> "DarwinClient[DarwinSymbol]": ...

    async def _objc_call(self, selector: str, *params, **kwargs) -> Any:
        """call an objc method on a given object"""
        sel = await self._client.symbols.sel_getUid(selector)
        if not await self._client.symbols.objc_msgSend(
            self, await self._client.symbols.sel_getUid("respondsToSelector:"), sel
        ):
            raise UnrecognizedSelectorError(f"unrecognized selector '{selector}' sent to class")

        return await self._client.symbols.objc_msgSend(self, sel, *params, **kwargs)

    async def objc_call(self, selector: str, *params: RemoteCallArg, va_list_index: int | None = None) -> Self:
        """call an objc method on a given object and return a symbol"""
        return await self._objc_call(selector, *params, va_list_index=va_list_index)

    async def objc_call_raw(self, selector: str, *params: RemoteCallArg, **kwargs) -> Any:
        """call an objc method on a given object and return a symbol"""
        return await self._objc_call(selector, *params, **kwargs, return_raw=True)

    async def py(
        self, typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = CfSerializableAny
    ) -> CfSerializableT:
        """get a python object from a core foundation one

        :param typ: Ensure that the returned Python object is of the given type.
        """
        return assert_cast(typ, await self._client.decode_cf(self) if self != 0 else None)

    async def region(self) -> "Region | None":
        """get corresponding region"""
        proc = await self._client.processes.get_by_pid(await self._client.get_pid())
        for region in await proc.get_regions():
            if (self >= region.start) and (self <= region.end):
                return region

    async def get_cfdesc(self, typ: type[CfSerializableT] = CfSerializableAny) -> CfSerializableT:
        """
        Get output from CFCopyDescription()
        :return: CFCopyDescription()'s output as a string
        """
        if self == 0:
            return assert_cast(typ, None)
        return await (await self._client.symbols.CFCopyDescription(self)).py(typ)

    async def cfdesc(self) -> CfSerializable:
        """
        Get output from CFCopyDescription()
        :return: CFCopyDescription()'s output as a string
        """
        return await self.get_cfdesc()

    @property
    def osstatus(self) -> list[ErrorCode] | None:
        """Get possible translation to given error code by querying osstatus"""
        return get_possible_error_codes(self)


class DarwinSymbol(Symbol, AbstractDarwinSymbol):
    @readonly
    def _client(self) -> "DarwinClient[Self]": ...

    def __init__(self, value: int, client: "DarwinClient[Self]") -> None:
        super().__init__(value, client)

    @property
    def objc_symbol(self) -> "ObjectiveCSymbol[Self]":
        """
        Get an ObjectiveC symbol of the same address
        :return: Object representing the ObjectiveC symbol
        """
        return self._client.objc_symbol(self)

    @property
    def stripped_value(self) -> Self:
        """Remove PAC upper bits"""
        return self._client.symbol(self & 0xFFFFFFFFF)
