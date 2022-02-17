from typing import Mapping

from rpcclient.exceptions import RpcClientException
from rpcclient.allocated import Allocated


class IOService(Allocated):
    """ representation of a remote IOService """

    def __init__(self, client, service):
        super().__init__()
        self._client = client
        self._service = service

    def set(self, properties: Mapping):
        self._client.symbols.IORegistryEntrySetCFProperties(self._service, self._client.cf(properties))

    def get(self, key: str):
        return self._client.symbols.IORegistryEntryCreateCFProperty(self._service, self._client.cf(key), 0, 0).py

    def _deallocate(self):
        self._client.symbols.IOObjectRelease(self._service)


class BacklightControlService(IOService):
    @property
    def display_parameters(self) -> Mapping:
        return self.get('IODisplayParameters')

    @property
    def brightness(self) -> int:
        return self.display_parameters['brightness']['value']

    @brightness.setter
    def brightness(self, value: int):
        self.set({'EnableBacklight': bool(value)})
        self.set({'brightness': value})


class PowerSourceService(IOService):
    @property
    def battery_voltage(self) -> int:
        return self.get('AppleRawBatteryVoltage')

    @property
    def charging(self) -> bool:
        return self.get('IsCharging')

    @charging.setter
    def charging(self, value: bool):
        self.set({'IsCharging': value, 'ExternalConnected': value})

    @property
    def external_connected(self) -> bool:
        return self.get('ExternalConnected')

    @external_connected.setter
    def external_connected(self, value: bool):
        self.set({'ExternalConnected': value})

    @property
    def current_capacity(self) -> int:
        return self.get('CurrentCapacity')

    @current_capacity.setter
    def current_capacity(self, value: int):
        self.set({'CurrentCapacity': value})

    @property
    def at_warn_level(self) -> bool:
        return self.get('AtWarnLevel')

    @at_warn_level.setter
    def at_warn_level(self, value: bool):
        self.set({'AtWarnLevel': value})

    @property
    def time_remaining(self) -> int:
        return self.get('TimeRemaining')

    @property
    def temperature(self) -> int:
        return self.get('Temperature')

    @temperature.setter
    def temperature(self, value: int):
        self.set({'Temperature': value})


class IOKit:
    """ IORegistry utils """

    def __init__(self, client):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client

    @property
    def backlight_control(self) -> IOService:
        return self.get_ioservice_by_property({'backlight-control': True}, cls=BacklightControlService)

    @property
    def power_source(self) -> IOService:
        return self.get_ioservice_by_service_name('IOPMPowerSource', cls=PowerSourceService)

    def get_ioservice_by_service_name(self, service_name: str, cls=IOService) -> IOService:
        service = self._client.symbols.IOServiceGetMatchingService(0,
                                                                   self._client.symbols.IOServiceMatching(service_name))
        if not service:
            raise RpcClientException(f'IOServiceGetMatchingService failed for: {service_name}')
        return cls(self._client, service)

    def get_ioservice_by_property(self, property_: Mapping, cls=IOService) -> IOService:
        service = self._client.symbols.IOServiceGetMatchingService(0, self._client.cf({'IOPropertyMatch': property_}))
        if not service:
            raise RpcClientException(f'IOServiceGetMatchingService failed for: {property_}')
        return cls(self._client, service)
