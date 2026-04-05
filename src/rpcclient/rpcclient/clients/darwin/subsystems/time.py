from datetime import datetime
from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.structs import timeval
from rpcclient.core._types import ClientBound


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient


class Time(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client
        client.load_framework_lazy("CoreTime")

    @zyncio.zmethod
    async def now(self) -> datetime:
        """get current time"""
        async with self._client.safe_calloc.z(timeval.sizeof()) as current:
            await self._client.symbols.gettimeofday.z(current, 0)
            time_of_day = await current.parse.z(timeval)
        return datetime.fromtimestamp(time_of_day.tv_sec + (time_of_day.tv_usec / (10**6)))

    @zyncio.zmethod
    async def set_current(self, new_time: datetime) -> None:
        """set current time"""
        await self._client.symbols.TMSetAutomaticTimeZoneEnabled.z(0)
        async with self._client.safe_calloc.z(timeval.sizeof()) as current:
            await current.poke.z(timeval.build({"tv_sec": int(new_time.timestamp()), "tv_usec": new_time.microsecond}))
            await self._client.symbols.settimeofday.z(current, 0)

    @zyncio.zmethod
    async def set_auto(self) -> None:
        """opt-in automatic time settings"""
        await self._client.symbols.TMSetAutomaticTimeZoneEnabled.z(1)

    @zyncio.zproperty
    async def is_set_automatically(self) -> bool:
        """tell is time settings are set to automatic"""
        return bool(await self._client.symbols.TMIsAutomaticTimeZoneEnabled.z())

    @zyncio.zmethod
    async def boot_time(self) -> datetime:
        timestamp = timeval.parse(await self._client.sysctl.get_by_name.z("kern.boottime")).tv_sec
        return datetime.fromtimestamp(timestamp)
