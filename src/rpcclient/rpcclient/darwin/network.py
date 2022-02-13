import ctypes
import logging
from typing import List

from rpcclient.exceptions import BadReturnValueError
from rpcclient.network import Network

logger = logging.getLogger(__name__)


class WifiNetwork:
    def __init__(self, client, interface, network):
        self._client = client
        self._interface = interface
        self._network = network

    @property
    def ssid(self) -> bytes:
        return self._network.get('SSID')

    @property
    def bssid(self) -> str:
        return self._network.get('BSSID')

    @property
    def rssi(self) -> int:
        return ctypes.c_int64(self._network['RSSI']).value

    @property
    def channel(self) -> int:
        return self._network['CHANNEL']

    def connect(self, password: str):
        """ connect to wifi network """
        if self._client.symbols.Apple80211Associate(self._interface, self._client.cf(self._network),
                                                    self._client.cf(password)):
            raise BadReturnValueError(f'Apple80211Associate failed ({self._client.last_error})')

    def __repr__(self):
        result = '<'
        result += f'SSID:{self.ssid} '
        result += f'BSSID:{self.bssid} '
        result += f'CHANNEL:{self.channel} '
        result += f'RSSI:{self.rssi}'
        result += '>'
        return result


class WifiInterface:
    def __init__(self, client, interface):
        self._client = client
        self._interface = interface

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def scan(self) -> List[WifiNetwork]:
        """ perform wifi scan """
        result = []
        with self._client.safe_malloc(8) as p_found_networks:
            if self._client.symbols.Apple80211Scan(self._interface, p_found_networks, self._client.cf({})):
                raise BadReturnValueError(f'Apple80211Scan failed ({self._client.last_error})')

            for network in p_found_networks[0].py:
                result.append(WifiNetwork(self._client, self, network))

        return result

    def disconnect(self):
        """ disconnect from current wifi network """
        self._client.symbols.Apple80211Disassociate(self._interface)

    def close(self):
        self._client.symbols.Apple80211Close(self._interface)


class DarwinNetwork(Network):
    def __init__(self, client):
        super().__init__(client)
        self._load_wifi_library()

    def _load_wifi_library(self):
        options = [
            # macOS
            '/System/Library/Frameworks/CoreWLAN.framework/Versions/A/CoreWLAN',
            '/System/Library/Frameworks/CoreWLAN.framework/CoreWLAN',
            # iOS
            '/System/Library/PrivateFrameworks/WiFiKit.framework/WiFiKit'
         ]
        for option in options:
            if self._client.dlopen(option, 2):
                return
        logger.warning('WiFi library isn\'t available')

    def get_wifi_interface(self, interface_name: str) -> WifiInterface:
        with self._client.safe_malloc(8) as p_interface:
            if self._client.symbols.Apple80211Open(p_interface):
                raise BadReturnValueError(f'Apple80211Open failed ({self._client.last_error})')
            if self._client.symbols.Apple80211BindToInterface(p_interface[0], self._client.cf(interface_name)):
                raise BadReturnValueError(f'Apple80211BindToInterface failed ({self._client.last_error})')
            return WifiInterface(self._client, p_interface[0])
