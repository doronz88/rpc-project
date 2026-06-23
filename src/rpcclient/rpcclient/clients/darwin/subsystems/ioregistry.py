from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Generic, TypeVar, cast
from typing_extensions import Self

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.common import CfSerializable
from rpcclient.clients.darwin.consts import MACH_PORT_NULL, kCFAllocatorDefault, kIOServicePlane
from rpcclient.clients.darwin.structs import io_name_t, io_object_t, mach_port_t
from rpcclient.core._types import ClientBound
from rpcclient.core.allocated import Allocated
from rpcclient.exceptions import BadReturnValueError, RpcClientException


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient


CfSerializableT = TypeVar("CfSerializableT", bound=CfSerializable)
_CfSerializableAny = cast(type[CfSerializable], object)


class IOService(Allocated["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """representation of a remote IOService"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]", service: DarwinSymbolT_co, name: str) -> None:
        super().__init__()
        self._client = client
        self._service: DarwinSymbolT_co = service
        self.name: str = name

    @classmethod
    async def create(cls, client: "DarwinClient[DarwinSymbolT_co]", service: int) -> Self:
        async with client.safe_malloc(io_name_t.sizeof()) as name:
            if await client.symbols.IORegistryEntryGetName(service, name):
                raise BadReturnValueError("IORegistryEntryGetName failed")
            name = await name.peek_str()

        return cls(client, client.symbol(service), name)

    async def properties(self) -> dict:
        async with self._client.safe_malloc(8) as p_properties:
            if await self._client.symbols.IORegistryEntryCreateCFProperties(
                self._service, p_properties, kCFAllocatorDefault, 0
            ):
                raise BadReturnValueError("IORegistryEntryCreateCFProperties failed")
            return await (await p_properties.getindex(0)).py(dict)

    async def _iter(self) -> "AsyncGenerator[IOService[DarwinSymbolT_co]]":
        async with self._client.safe_malloc(io_object_t.sizeof()) as p_child_iter:
            if await self._client.symbols.IORegistryEntryGetChildIterator(self._service, kIOServicePlane, p_child_iter):
                raise BadReturnValueError("IORegistryEntryGetChildIterator failed")
            child_iter = await p_child_iter.getindex(0)

        while child := await self._client.symbols.IOIteratorNext(child_iter):
            yield await IOService.create(self._client, child)

    def __aiter__(self) -> "AsyncGenerator[IOService[DarwinSymbolT_co]]":
        return self._iter()

    async def set(self, properties: dict) -> None:
        await self._client.symbols.IORegistryEntrySetCFProperties(self._service, await self._client.cf(properties))

    async def get(
        self, key: str, typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = _CfSerializableAny
    ) -> CfSerializableT:
        return await (
            await self._client.symbols.IORegistryEntryCreateCFProperty(
                self._service, await self._client.cf(key), kCFAllocatorDefault, 0
            )
        ).py(typ)

    async def _deallocate(self) -> None:
        await self._client.symbols.IOObjectRelease(self._service)

    def __repr__(self):
        return f"<{self.__class__.__name__} NAME:{self.name}>"


class BacklightControlService(IOService[DarwinSymbolT_co]):
    async def display_parameters(self) -> dict:
        return await self.get("IODisplayParameters", dict)

    async def get_brightness(self) -> int:
        return (await type(self).display_parameters(self))["brightness"]["value"]

    async def set_brightness(self, value: int) -> None:
        await self.set({"EnableBacklight": bool(value)})
        await self.set({"brightness": value})


class PowerSourceService(IOService[DarwinSymbolT_co]):
    async def battery_voltage(self) -> int:
        return await self.get("AppleRawBatteryVoltage", int)

    async def get_charging(self) -> bool:
        return await self.get("IsCharging", bool)

    async def set_charging(self, value: bool) -> None:
        await self.set({"IsCharging": value, "ExternalConnected": value})

    async def get_external_connected(self) -> bool:
        return await self.get("ExternalConnected", bool)

    async def set_external_connected(self, value: bool) -> None:
        await self.set({"ExternalConnected": value})

    async def get_current_capacity(self) -> int:
        return await self.get("CurrentCapacity", int)

    async def set_current_capacity(self, value: int) -> None:
        await self.set({"CurrentCapacity": value})

    async def get_at_warn_level(self) -> bool:
        return await self.get("AtWarnLevel", bool)

    async def set_at_warn_level(self, value: bool) -> None:
        await self.set({"AtWarnLevel": value})

    async def time_remaining(self) -> int:
        return await self.get("TimeRemaining", int)

    async def get_temperature(self) -> int:
        return await self.get("Temperature", int)

    async def set_temperature(self, value: int) -> None:
        await self.set({"Temperature": value})


class IORegistry(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    IORegistry utils
    https://developer.apple.com/library/archive/documentation/DeviceDrivers/Conceptual/IOKitFundamentals/TheRegistry/TheRegistry.html
    """

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client

    async def backlight_control(self) -> BacklightControlService[DarwinSymbolT_co]:
        service = await self._client.symbols.IOServiceGetMatchingService(
            0, await self._client.cf({"IOPropertyMatch": {"backlight-control": True}})
        )
        if not service:
            raise RpcClientException("IOServiceGetMatchingService failed")
        return await BacklightControlService.create(self._client, service)

    async def power_source(self) -> PowerSourceService[DarwinSymbolT_co]:
        service = await self._client.symbols.IOServiceGetMatchingService(
            0, await self._client.symbols.IOServiceMatching("IOPMPowerSource")
        )
        if not service:
            raise RpcClientException("IOServiceGetMatchingService failed")
        return await PowerSourceService.create(self._client, service)

    async def root(self) -> IOService[DarwinSymbolT_co]:
        async with self._client.safe_malloc(mach_port_t.sizeof()) as p_master_port:
            await self._client.symbols.IOMasterPort(MACH_PORT_NULL, p_master_port)
            return await IOService.create(
                self._client, await self._client.symbols.IORegistryGetRootEntry(await p_master_port.getindex(0))
            )
