import ctypes
import logging
from typing import List

from rpcclient.allocated import Allocated
from rpcclient.exceptions import RpcClientException
from rpcclient.network import Network
from rpcclient.structs.consts import RTLD_NOW

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
            self._client.raise_errno_exception('Apple80211Associate failed')

    def __repr__(self):
        result = '<'
        result += f'SSID:{self.ssid} '
        result += f'BSSID:{self.bssid} '
        result += f'CHANNEL:{self.channel} '
        result += f'RSSI:{self.rssi}'
        result += '>'
        return result


class WifiInterface(Allocated):
    def __init__(self, client, interface, wifi_manager_client, device):
        super().__init__()
        self._client = client
        self._interface = interface
        self._wifi_manager_client = wifi_manager_client
        self._device = device

    def scan(self) -> List[WifiNetwork]:
        """ perform wifi scan """
        result = []
        with self._client.safe_malloc(8) as p_found_networks:
            if self._client.symbols.Apple80211Scan(self._interface, p_found_networks, self._client.cf({})):
                self._client.raise_errno_exception('Apple80211Scan failed')

            for network in p_found_networks[0].py():
                result.append(WifiNetwork(self._client, self, network))

        return result

    def disconnect(self):
        """ disconnect from current wifi network """
        self._client.symbols.Apple80211Disassociate(self._interface)

    def _set(self, is_on: bool):
        with self._client.preferences.sc.open('com.apple.wifi.plist') as pref:
            pref.set('AllowEnable', int(is_on))

        if not is_on:
            if self._client.symbols.WiFiManagerClientDisable(self._wifi_manager_client):
                self._client.raise_errno_exception('WiFiManagerClientDisable failed')

        if self._client.symbols.WiFiDeviceClientSetPower(self._device, is_on):
            self._client.raise_errno_exception('WiFiDeviceClientSetPower failed')

        if is_on:
            if self._client.symbols.WiFiManagerClientEnable(self._wifi_manager_client):
                self._client.raise_errno_exception('WiFiManagerClientEnable failed')

    def turn_on(self):
        self._set(True)

    def turn_off(self):
        self._set(False)

    def is_on(self) -> bool:
        return self._client.symbols.WiFiDeviceClientGetPower(self._device) == 1

    def _deallocate(self):
        self._client.symbols.Apple80211Close(self._interface)


class DarwinNetwork(Network):
    """ network utils """

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
            if self._client.dlopen(option, RTLD_NOW):
                return
        logger.warning('WiFi library isn\'t available')

    def set_airplane_mode(self, mode: bool):
        """ set whether the device should enter airplane mode (turns off baseband, bt, etc...) """
        preferences = self._client.symbols.objc_getClass('RadiosPreferences').objc_call('new')
        preferences.objc_call('setAirplaneMode:', mode)
        preferences.objc_call('synchronize')

    @property
    def wifi_interfaces(self) -> List[str]:
        """ get a list of all available wifi interfaces """
        with self._client.safe_malloc(8) as p_interface:
            if self._client.symbols.Apple80211Open(p_interface):
                self._client.raise_errno_exception('Apple80211Open failed')

            with self._client.safe_malloc(8) as p_interface_names:
                if self._client.symbols.Apple80211GetIfListCopy(p_interface[0], p_interface_names):
                    self._client.raise_errno_exception('Apple80211GetIfListCopy failed')

                return p_interface_names[0].py()

    def get_wifi_interface(self, interface_name: str = None) -> WifiInterface:
        """ get a specific wifi interface object for remote controlling """
        with self._client.safe_malloc(8) as p_handle:
            if self._client.symbols.Apple80211Open(p_handle):
                self._client.raise_errno_exception('Apple80211Open failed')
            handle = p_handle[0]

        if interface_name is None:
            wifi_interfaces = self.wifi_interfaces

            if not wifi_interfaces:
                raise RpcClientException('no available wifi interfaces were found')

            interface_name = wifi_interfaces[0]

        if self._client.symbols.Apple80211BindToInterface(handle, self._client.cf(interface_name)):
            self._client.raise_errno_exception('Apple80211BindToInterface failed')

        wifi_manager_client = self._client.symbols.WiFiManagerClientCreate(0, 0)
        if not wifi_manager_client:
            self._client.raise_errno_exception('WiFiManagerClientCreate failed')

        device = self._client.symbols.WiFiManagerClientGetDevice(wifi_manager_client,
                                                                 self._client.cf(interface_name))
        if not device:
            self._client.raise_errno_exception('WiFiManagerClientGetDevice failed')

        return WifiInterface(self._client, handle, wifi_manager_client, device)
