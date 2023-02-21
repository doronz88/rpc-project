from typing import Mapping

from rpcclient.allocated import Allocated
from rpcclient.darwin.consts import MACH_PORT_NULL, kCFAllocatorDefault, kIOServicePlane
from rpcclient.darwin.structs import io_name_t, io_object_t, mach_port_t
from rpcclient.exceptions import BadReturnValueError, RpcClientException


class IOService(Allocated):
    """ representation of a remote IOService """

    def __init__(self, client, service):
        super().__init__()
        self._client = client
        self._service = service

    @property
    def name(self) -> str:
        with self._client.safe_malloc(io_name_t.sizeof()) as name:
            if self._client.symbols.IORegistryEntryGetName(self._service, name):
                raise BadReturnValueError('IORegistryEntryGetName failed')
            return name.peek_str()

    @property
    def properties(self) -> Mapping:
        with self._client.safe_malloc(8) as p_properties:
            if self._client.symbols.IORegistryEntryCreateCFProperties(self._service, p_properties,
                                                                      kCFAllocatorDefault, 0):
                raise BadReturnValueError('IORegistryEntryCreateCFProperties failed')
            return p_properties[0].py()

    def __iter__(self):
        with self._client.safe_malloc(io_object_t.sizeof()) as p_child_iter:
            if self._client.symbols.IORegistryEntryGetChildIterator(self._service, kIOServicePlane, p_child_iter):
                raise BadReturnValueError('IORegistryEntryGetChildIterator failed')
            child_iter = p_child_iter[0]

        while True:
            child = self._client.symbols.IOIteratorNext(child_iter)
            if not child:
                break
            s = IOService(self._client, child)
            yield s

    def set(self, properties: Mapping):
        self._client.symbols.IORegistryEntrySetCFProperties(self._service, self._client.cf(properties))

    def get(self, key: str):
        return self._client.symbols.IORegistryEntryCreateCFProperty(self._service, self._client.cf(key),
                                                                    kCFAllocatorDefault, 0).py()

    def _deallocate(self):
        self._client.symbols.IOObjectRelease(self._service)

    def __repr__(self):
        return f'<{self.__class__.__name__} NAME:{self.name}>'


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


class IORegistry:
    """
    IORegistry utils
    https://developer.apple.com/library/archive/documentation/DeviceDrivers/Conceptual/IOKitFundamentals/TheRegistry/TheRegistry.html
    """

    def __init__(self, client):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client

    @property
    def backlight_control(self) -> BacklightControlService:
        service = self._client.symbols.IOServiceGetMatchingService(
            0, self._client.cf({'IOPropertyMatch': {'backlight-control': True}}))
        if not service:
            raise RpcClientException('IOServiceGetMatchingService failed')
        return BacklightControlService(self._client, service)

    @property
    def power_source(self) -> PowerSourceService:
        service = self._client.symbols.IOServiceGetMatchingService(
            0, self._client.symbols.IOServiceMatching('IOPMPowerSource'))
        if not service:
            raise RpcClientException('IOServiceGetMatchingService failed')
        return PowerSourceService(self._client, service)

    @property
    def root(self) -> IOService:
        with self._client.safe_malloc(mach_port_t.sizeof()) as p_master_port:
            self._client.symbols.IOMasterPort(MACH_PORT_NULL, p_master_port)
            return IOService(self._client, self._client.symbols.IORegistryGetRootEntry(p_master_port[0]))
