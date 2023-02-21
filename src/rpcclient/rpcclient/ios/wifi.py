import ctypes
import logging
from typing import List, Mapping

from rpcclient.allocated import Allocated
from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.exceptions import BadReturnValueError, RpcClientException
from rpcclient.structs.consts import RTLD_NOW

logger = logging.getLogger(__name__)


class WifiSavedNetwork:
    def __init__(self, client, wifi_manager: DarwinSymbol, network: DarwinSymbol):
        self._client = client
        self._wifi_manager = wifi_manager
        self._network = network

    @property
    def ssid(self) -> bytes:
        return self.get_property('SSID')

    @property
    def bssid(self) -> str:
        return self.get_property('BSSID')

    def get_property(self, name: str):
        return self._client.symbols.WiFiNetworkGetProperty(self._network, self._client.cf(name)).py()

    def forget(self):
        """ forget Wi-Fi network """
        self._client.symbols.WiFiManagerClientRemoveNetwork(self._wifi_manager, self._network)

    def __repr__(self):
        result = f'<{self.__class__.__name__} '
        result += f'SSID:{self.ssid} '
        result += f'BSSID:{self.bssid}'
        result += '>'
        return result


class WifiScannedNetwork:
    def __init__(self, client, interface: DarwinSymbol, network: Mapping):
        self._client = client
        self._interface = interface
        self.network = network

    @property
    def ssid(self) -> bytes:
        return self.network.get('SSID')

    @property
    def bssid(self) -> str:
        return self.network.get('BSSID')

    @property
    def rssi(self) -> int:
        return ctypes.c_int64(self.network['RSSI']).value

    @property
    def channel(self) -> int:
        return self.network['CHANNEL']

    def connect(self, password: str = None):
        """ connect to Wi-Fi network """
        result = self._client.symbols.Apple80211Associate(self._interface, self._client.cf(self.network),
                                                          self._client.cf(password) if password else 0)

        if result:
            raise BadReturnValueError(f'Apple80211Associate() failed with: {result}')

    def disconnect(self):
        if self._client.symbols.Apple80211Disassociate(self._interface):
            raise BadReturnValueError('Apple80211Disassociate() failed')

    def __repr__(self):
        result = f'<{self.__class__.__name__} '
        result += f'SSID:{self.ssid} '
        result += f'BSSID:{self.bssid} '
        result += f'CHANNEL:{self.channel} '
        result += f'RSSI:{self.rssi}'
        result += '>'
        return result


class WifiInterface(Allocated):
    def __init__(self, client, interface, device):
        super().__init__()
        self._client = client
        self._interface = interface
        self._device = device

    def scan(self, options: Mapping = None) -> List[WifiScannedNetwork]:
        """ perform Wi-Fi scan """

        if options is None:
            options = {}

        result = []
        with self._client.safe_malloc(8) as p_found_networks:
            while True:
                scan_result = self._client.symbols.Apple80211Scan(self._interface, p_found_networks,
                                                                  self._client.cf(options))
                if scan_result == 0:
                    break
                elif scan_result == -1:
                    raise BadReturnValueError('Apple80211Scan failed')
                # else, try again

            for network in p_found_networks[0].py():
                result.append(WifiScannedNetwork(self._client, self._interface, network))

        return result

    def disconnect(self):
        """ disconnect from current Wi-Fi network """
        self._client.symbols.Apple80211Disassociate(self._interface)

    def _deallocate(self):
        self._client.symbols.Apple80211Close(self._interface)


class IosWifi:
    """ network utils """

    def __init__(self, client):
        self._client = client
        self._load_wifi_library()

        self._wifi_manager = self._client.symbols.WiFiManagerClientCreate(0, 0)
        if not self._wifi_manager:
            self._client.raise_errno_exception('WiFiManagerClientCreate failed')

    @property
    def saved_networks(self) -> List[WifiSavedNetwork]:
        result = []

        network_list = self._client.symbols.WiFiManagerClientCopyNetworks(self._wifi_manager).py()
        if not network_list:
            return result

        for network in network_list:
            result.append(WifiSavedNetwork(self._client, self._wifi_manager, network))

        return result

    @property
    def interfaces(self) -> List[str]:
        """ get a list of all available wifi interfaces """
        with self._client.safe_malloc(8) as p_interface:
            if self._client.symbols.Apple80211Open(p_interface):
                self._client.raise_errno_exception('Apple80211Open() failed')

            with self._client.safe_malloc(8) as p_interface_names:
                if self._client.symbols.Apple80211GetIfListCopy(p_interface[0], p_interface_names):
                    self._client.raise_errno_exception('Apple80211GetIfListCopy() failed')

                return p_interface_names[0].py()

    def turn_on(self):
        self._set(True)

    def turn_off(self):
        self._set(False)

    def is_on(self) -> bool:
        return bool(self._client.symbols.WiFiManagerClientCopyProperty(self._wifi_manager,
                                                                       self._client.cf('AllowEnable')).py())

    def get_interface(self, interface_name: str = None) -> WifiInterface:
        """ get a specific wifi interface object for remote controlling """
        with self._client.safe_malloc(8) as p_handle:
            if self._client.symbols.Apple80211Open(p_handle):
                self._client.raise_errno_exception('Apple80211Open() failed')
            handle = p_handle[0]

        if interface_name is None:
            wifi_interfaces = self.interfaces

            if not wifi_interfaces:
                raise RpcClientException('no available wifi interfaces were found')

            interface_name = wifi_interfaces[0]

        if self._client.symbols.Apple80211BindToInterface(handle, self._client.cf(interface_name)):
            self._client.raise_errno_exception('Apple80211BindToInterface failed')

        device = self._client.symbols.WiFiManagerClientGetDevice(self._wifi_manager,
                                                                 self._client.cf(interface_name))
        if not device:
            self._client.raise_errno_exception('WiFiManagerClientGetDevice failed')

        return WifiInterface(self._client, handle, device)

    def _load_wifi_library(self):
        options = [
            # macOS
            '/System/Library/Frameworks/CoreWLAN.framework/Versions/A/CoreWLAN',
            '/System/Library/Frameworks/CoreWLAN.framework/CoreWLAN',
            # iOS
            '/System/Library/PrivateFrameworks/WiFiKit.framework/WiFiKit'
        ]
        for option in options:
            if self._client.dlopen(option, RTLD_NOW):
                return
        logger.warning('WiFi library isn\'t available')

    def _set(self, is_on: bool):
        if not self._client.symbols.WiFiManagerClientSetProperty(self._wifi_manager,
                                                                 self._client.cf('AllowEnable'),
                                                                 self._client.cf(is_on)):
            raise BadReturnValueError('WiFiManagerClientSetProperty() failed')
