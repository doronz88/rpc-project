from enum import Enum
from typing import Optional

from rpcclient.exceptions import RpcPermissionError


class CLAuthorizationStatus(Enum):
    kCLAuthorizationStatusNotDetermined = 0
    kCLAuthorizationStatusRestricted = 1
    kCLAuthorizationStatusDenied = 2
    kCLAuthorizationStatusAuthorizedAlways = 3
    kCLAuthorizationStatusAuthorizedWhenInUse = 4
    kCLAuthorizationStatusAuthorized = kCLAuthorizationStatusAuthorizedAlways

    @classmethod
    def from_value(cls, value: int):
        for i in cls:
            if i.value == value:
                return i


class Location:
    """
    Wrapper to CLLocationManager
    https://developer.apple.com/documentation/corelocation/cllocationmanager?language=objc
    """

    def __init__(self, client):
        self._client = client
        self._client.load_framework('CoreLocation')

        self._CLLocationManager = self._client.symbols.objc_getClass('CLLocationManager')
        self._location_manager = self._CLLocationManager.objc_call('sharedManager')

    @property
    def location_services_enabled(self) -> bool:
        """ opt-in status for location services """
        return bool(self._location_manager.objc_call('locationServicesEnabled'))

    @location_services_enabled.setter
    def location_services_enabled(self, value: bool):
        """ opt-in status for location services """
        self._CLLocationManager.objc_call('setLocationServicesEnabled:', value)

    @property
    def authorization_status(self) -> CLAuthorizationStatus:
        """ authorization status for current server process of accessing location services """
        return CLAuthorizationStatus.from_value(self._location_manager.objc_call('authorizationStatus'))

    @property
    def last_sample(self) -> Optional[dict]:
        """ last taken location sample (or None if there isn't any) """
        location = self._location_manager.objc_call('location')
        if not location:
            return None
        return location.objc_call('jsonObject').py()

    def request_always_authorization(self) -> None:
        """ Request authorization to always query location data """
        self._location_manager.objc_call('requestAlwaysAuthorization')

    def start_updating_location(self):
        """ request location updates from CLLocationManager """
        if self.authorization_status.value < CLAuthorizationStatus.kCLAuthorizationStatusAuthorizedAlways.value:
            raise RpcPermissionError()
        self._location_manager.objc_call('startUpdatingLocation')

    def stop_updating_location(self):
        """ stop requesting location updates from CLLocationManager """
        self._location_manager.objc_call('stopUpdatingLocation')

    def request_oneshot_location(self):
        """ requests the one-time delivery of the user’s current location """
        if self.authorization_status.value < CLAuthorizationStatus.kCLAuthorizationStatusAuthorizedAlways.value:
            raise RpcPermissionError()
        self._location_manager.objc_call('requestLocation')
