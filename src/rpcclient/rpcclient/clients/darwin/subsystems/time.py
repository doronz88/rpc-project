from datetime import datetime
from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.structs import timeval
from rpcclient.core._types import ClientBound


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient


class Time(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client
        client.load_framework_lazy("CoreTime")

    async def now(self) -> datetime:
        """get current time"""
        async with self._client.safe_calloc(timeval.sizeof()) as current:
            await self._client.symbols.gettimeofday(current, 0)
            time_of_day = await current.parse(timeval)
        return datetime.fromtimestamp(time_of_day.tv_sec + (time_of_day.tv_usec / (10**6)))

    async def set_current(self, new_time: datetime) -> None:
        """set current time"""
        await self._client.symbols.TMSetAutomaticTimeZoneEnabled(0)
        async with self._client.safe_calloc(timeval.sizeof()) as current:
            await current.poke(timeval.build({"tv_sec": int(new_time.timestamp()), "tv_usec": new_time.microsecond}))
            await self._client.symbols.settimeofday(current, 0)

    async def set_auto(self) -> None:
        """opt-in automatic time settings"""
        await self._client.symbols.TMSetAutomaticTimeZoneEnabled(1)

    async def is_set_automatically(self) -> bool:
        """tell is time settings are set to automatic"""
        return bool(await self._client.symbols.TMIsAutomaticTimeZoneEnabled())

    async def boot_time(self) -> datetime:
        timestamp = timeval.parse(await self._client.sysctl.get_by_name("kern.boottime")).tv_sec
        return datetime.fromtimestamp(timestamp)
