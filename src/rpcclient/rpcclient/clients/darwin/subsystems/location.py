from enum import Enum
from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import RpcPermissionError
from rpcclient.utils import cached_async_method


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient


class CLAuthorizationStatus(Enum):
    kCLAuthorizationStatusNotDetermined = 0
    kCLAuthorizationStatusRestricted = 1
    kCLAuthorizationStatusDenied = 2
    kCLAuthorizationStatusAuthorizedAlways = 3
    kCLAuthorizationStatusAuthorizedWhenInUse = 4
    kCLAuthorizationStatusAuthorized = kCLAuthorizationStatusAuthorizedAlways


class Location(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Wrapper to CLLocationManager
    https://developer.apple.com/documentation/corelocation/cllocationmanager?language=objc
    """

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client
        client.load_framework_lazy("CoreLocation")

    @cached_async_method
    async def _get_CLLocationManager(self) -> DarwinSymbolT_co:
        return await self._client.symbols.objc_getClass("CLLocationManager")

    @cached_async_method
    async def _get_location_manager(self) -> DarwinSymbolT_co:
        return await (await self._get_CLLocationManager()).objc_call("sharedManager")

    async def get_location_services_enabled(self) -> bool:
        """opt-in status for location services"""
        return bool(await (await self._get_location_manager()).objc_call("locationServicesEnabled"))

    async def set_location_services_enabled(self, value: bool) -> None:
        """opt-in status for location services"""
        await (await self._get_CLLocationManager()).objc_call("setLocationServicesEnabled:", value)

    async def authorization_status(self) -> CLAuthorizationStatus:
        """authorization status for current server process of accessing location services"""
        return CLAuthorizationStatus((await self._get_location_manager()).objc_call("authorizationStatus"))

    async def last_sample(self) -> dict | None:
        """last taken location sample (or None if there isn't any)"""
        location = await (await self._get_location_manager()).objc_call("location")
        if not location:
            return None
        return await (await location.objc_call("jsonObject")).py(dict)

    async def request_always_authorization(self) -> None:
        """Request authorization to always query location data"""
        await (await self._get_location_manager()).objc_call("requestAlwaysAuthorization")

    async def start_updating_location(self) -> None:
        """request location updates from CLLocationManager"""
        if (
            await type(self).authorization_status(self)
        ).value < CLAuthorizationStatus.kCLAuthorizationStatusAuthorizedAlways.value:
            raise RpcPermissionError()
        await (await self._get_location_manager()).objc_call("startUpdatingLocation")

    async def stop_updating_location(self) -> None:
        """stop requesting location updates from CLLocationManager"""
        await (await self._get_location_manager()).objc_call("stopUpdatingLocation")

    async def request_oneshot_location(self) -> None:
        """requests the one-time delivery of the user's current location"""
        if (
            await type(self).authorization_status(self)
        ).value < CLAuthorizationStatus.kCLAuthorizationStatusAuthorizedAlways.value:
            raise RpcPermissionError()
        await (await self._get_location_manager()).objc_call("requestLocation")
