from collections.abc import AsyncGenerator, Generator
from typing import TYPE_CHECKING, Generic, TypeVar, cast
from typing_extensions import Self

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.common import CfSerializable
from rpcclient.clients.darwin.consts import MACH_PORT_NULL, kCFAllocatorDefault, kIOServicePlane
from rpcclient.clients.darwin.structs import io_name_t, io_object_t, mach_port_t
from rpcclient.clients.darwin.symbol import DarwinSymbol
from rpcclient.core._types import ClientBound
from rpcclient.core.allocated import Allocated
from rpcclient.exceptions import BadReturnValueError, RpcClientException


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient


CfSerializableT = TypeVar("CfSerializableT", bound=CfSerializable)
_CfSerializableAny = cast(type[CfSerializable], object)


class IOService(Allocated["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """representation of a remote IOService"""

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]", service: DarwinSymbolT_co, name: str) -> None:
        super().__init__()
        self._client = client
        self._service: DarwinSymbolT_co = service
        self.name: str = name

    @classmethod
    async def create(cls, client: "BaseDarwinClient[DarwinSymbolT_co]", service: int) -> Self:
        async with client.safe_malloc.z(io_name_t.sizeof()) as name:
            if await client.symbols.IORegistryEntryGetName.z(service, name):
                raise BadReturnValueError("IORegistryEntryGetName failed")
            name = await name.peek_str.z()

        return cls(client, client.symbol(service), name)

    @zyncio.zproperty
    async def properties(self) -> dict:
        async with self._client.safe_malloc.z(8) as p_properties:
            if await self._client.symbols.IORegistryEntryCreateCFProperties.z(
                self._service, p_properties, kCFAllocatorDefault, 0
            ):
                raise BadReturnValueError("IORegistryEntryCreateCFProperties failed")
            return await (await p_properties.getindex(0)).py.z(dict)

    @zyncio.zgeneratormethod
    async def _iter(self) -> "AsyncGenerator[IOService[DarwinSymbolT_co]]":
        async with self._client.safe_malloc.z(io_object_t.sizeof()) as p_child_iter:
            if await self._client.symbols.IORegistryEntryGetChildIterator.z(
                self._service, kIOServicePlane, p_child_iter
            ):
                raise BadReturnValueError("IORegistryEntryGetChildIterator failed")
            child_iter = await p_child_iter.getindex(0)

        while child := await self._client.symbols.IOIteratorNext.z(child_iter):
            yield await IOService.create(self._client, child)

    def __iter__(self: "IOService[DarwinSymbol]") -> "Generator[IOService[DarwinSymbol]]":
        return self._iter()

    def __aiter__(self) -> "AsyncGenerator[IOService[DarwinSymbolT_co]]":
        return self._iter.z()

    @zyncio.zmethod
    async def set(self, properties: dict) -> None:
        await self._client.symbols.IORegistryEntrySetCFProperties.z(self._service, await self._client.cf.z(properties))

    @zyncio.zmethod
    async def get(
        self, key: str, typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = _CfSerializableAny
    ) -> CfSerializableT:
        return await (
            await self._client.symbols.IORegistryEntryCreateCFProperty.z(
                self._service, await self._client.cf.z(key), kCFAllocatorDefault, 0
            )
        ).py.z(typ)

    async def _deallocate(self) -> None:
        await self._client.symbols.IOObjectRelease.z(self._service)

    def __repr__(self):
        return f"<{self.__class__.__name__} NAME:{self.name}>"


class BacklightControlService(IOService[DarwinSymbolT_co]):
    @zyncio.zproperty
    async def display_parameters(self) -> dict:
        return await self.get.z("IODisplayParameters", dict)

    @zyncio.zproperty
    async def _brightness(self) -> int:
        return await (await type(self).display_parameters(self))["brightness"]["value"]

    @_brightness.setter
    async def brightness(self, value: int) -> None:
        await self.set.z({"EnableBacklight": bool(value)})
        await self.set.z({"brightness": value})


class PowerSourceService(IOService[DarwinSymbolT_co]):
    @zyncio.zproperty
    async def battery_voltage(self) -> int:
        return await self.get.z("AppleRawBatteryVoltage", int)

    @zyncio.zproperty
    async def _charging(self) -> bool:
        return await self.get.z("IsCharging", bool)

    @_charging.setter
    async def charging(self, value: bool) -> None:
        await self.set.z({"IsCharging": value, "ExternalConnected": value})

    @zyncio.zproperty
    async def _external_connected(self) -> bool:
        return await self.get.z("ExternalConnected", bool)

    @_external_connected.setter
    async def external_connected(self, value: bool) -> None:
        await self.set.z({"ExternalConnected": value})

    @zyncio.zproperty
    async def _current_capacity(self) -> int:
        return await self.get.z("CurrentCapacity", int)

    @_current_capacity.setter
    async def current_capacity(self, value: int) -> None:
        await self.set.z({"CurrentCapacity": value})

    @zyncio.zproperty
    async def _at_warn_level(self) -> bool:
        return await self.get.z("AtWarnLevel", bool)

    @_at_warn_level.setter
    async def at_warn_level(self, value: bool) -> None:
        await self.set.z({"AtWarnLevel": value})

    @zyncio.zproperty
    async def time_remaining(self) -> int:
        return await self.get.z("TimeRemaining", int)

    @zyncio.zproperty
    async def _temperature(self) -> int:
        return await self.get.z("Temperature", int)

    @_temperature.setter
    async def temperature(self, value: int) -> None:
        await self.set.z({"Temperature": value})


class IORegistry(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    IORegistry utils
    https://developer.apple.com/library/archive/documentation/DeviceDrivers/Conceptual/IOKitFundamentals/TheRegistry/TheRegistry.html
    """

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client

    @zyncio.zproperty
    async def backlight_control(self) -> BacklightControlService[DarwinSymbolT_co]:
        service = await self._client.symbols.IOServiceGetMatchingService.z(
            0, await self._client.cf.z({"IOPropertyMatch": {"backlight-control": True}})
        )
        if not service:
            raise RpcClientException("IOServiceGetMatchingService failed")
        return await BacklightControlService.create(self._client, service)

    @zyncio.zproperty
    async def power_source(self) -> PowerSourceService[DarwinSymbolT_co]:
        service = await self._client.symbols.IOServiceGetMatchingService.z(
            0, await self._client.symbols.IOServiceMatching.z("IOPMPowerSource")
        )
        if not service:
            raise RpcClientException("IOServiceGetMatchingService failed")
        return await PowerSourceService.create(self._client, service)

    @zyncio.zproperty
    async def root(self) -> IOService[DarwinSymbolT_co]:
        async with self._client.safe_malloc.z(mach_port_t.sizeof()) as p_master_port:
            await self._client.symbols.IOMasterPort.z(MACH_PORT_NULL, p_master_port)
            return await IOService.create(
                self._client, await self._client.symbols.IORegistryGetRootEntry.z(await p_master_port.getindex(0))
            )
