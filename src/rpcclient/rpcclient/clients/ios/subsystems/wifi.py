import ctypes
import logging
from typing import TYPE_CHECKING, Optional

from rpcclient.clients.darwin.common import CfSerializable
from rpcclient.clients.darwin.symbol import DarwinSymbol
from rpcclient.core.allocated import Allocated
from rpcclient.exceptions import BadReturnValueError, RpcClientException

if TYPE_CHECKING:
    from rpcclient.clients.ios.client import IosClient

logger = logging.getLogger(__name__)


class WifiSavedNetwork:
    def __init__(self, client: "IosClient", wifi_manager: DarwinSymbol, network: DarwinSymbol) -> None:
        self._client = client
        self._wifi_manager = wifi_manager
        self._network = network

    @property
    def ssid(self) -> bytes:
        """Return the network SSID as raw bytes."""
        return self.get_property("SSID")

    @property
    def bssid(self) -> str:
        """Return the network BSSID as a string."""
        return self.get_property("BSSID")

    def get_property(self, name: str) -> CfSerializable:
        """Return a WiFiNetwork property by name from the underlying CF object."""
        return self._client.symbols.WiFiNetworkGetProperty(self._network, self._client.cf(name)).py()

    def forget(self) -> None:
        """Remove this network from the saved networks list."""
        self._client.symbols.WiFiManagerClientRemoveNetwork(self._wifi_manager, self._network)

    def __repr__(self) -> str:
        result = f"<{self.__class__.__name__} "
        result += f"SSID:{self.ssid} "
        result += f"BSSID:{self.bssid}"
        result += ">"
        return result


class WifiScannedNetwork:
    def __init__(self, client: "IosClient", interface: DarwinSymbol, network: dict) -> None:
        self._client = client
        self._interface = interface
        self.network = network

    @property
    def ssid(self) -> bytes:
        """Return the scanned network SSID as raw bytes."""
        return self.network.get("SSID")

    @property
    def bssid(self) -> str:
        """Return the scanned network BSSID as a string."""
        return self.network.get("BSSID")

    @property
    def rssi(self) -> int:
        """Return the received signal strength indicator (RSSI)."""
        return ctypes.c_int64(self.network["RSSI"]).value

    @property
    def channel(self) -> int:
        """Return the Wi-Fi channel number."""
        return self.network["CHANNEL"]

    def connect(self, password: Optional[str] = None) -> None:
        """Associate to this network, optionally providing a password."""
        result = self._client.symbols.Apple80211Associate(
            self._interface, self._client.cf(self.network), self._client.cf(password) if password else 0
        )

        if result:
            raise BadReturnValueError(f"Apple80211Associate() failed with: {result}")

    def disconnect(self) -> None:
        """Disassociate from the current network."""
        if self._client.symbols.Apple80211Disassociate(self._interface):
            raise BadReturnValueError("Apple80211Disassociate() failed")

    def __repr__(self) -> str:
        result = f"<{self.__class__.__name__} "
        result += f"SSID:{self.ssid} "
        result += f"BSSID:{self.bssid} "
        result += f"CHANNEL:{self.channel} "
        result += f"RSSI:{self.rssi}"
        result += ">"
        return result


class WifiInterface(Allocated):
    def __init__(self, client: "IosClient", interface: DarwinSymbol) -> None:
        super().__init__()
        self._client = client
        self._interface = interface

    def scan(self, options: Optional[dict] = None) -> list[WifiScannedNetwork]:
        """Scan for nearby networks and return a list of WifiScannedNetwork."""

        if options is None:
            options = {}

        result = []
        with self._client.safe_malloc(8) as p_found_networks:
            while True:
                scan_result = self._client.symbols.Apple80211Scan(
                    self._interface, p_found_networks, self._client.cf(options)
                )
                if scan_result == 0:
                    break
                elif scan_result == -1:
                    raise BadReturnValueError("Apple80211Scan failed")
                # else, try again

            for network in p_found_networks[0].py():
                result.append(WifiScannedNetwork(self._client, self._interface, network))

        return result

    def disconnect(self) -> None:
        """Disconnect from the currently associated Wi-Fi network."""
        self._client.symbols.Apple80211Disassociate(self._interface)

    def _deallocate(self) -> None:
        self._client.symbols.Apple80211Close(self._interface)


class IosWifi:
    """iOS Wi-Fi utilities backed by WiFiKit and Apple80211."""

    def __init__(self, client: "IosClient") -> None:
        self._client = client
        self._client.load_framework("WiFiKit")

        self._wifi_manager = self._client.symbols.WiFiManagerClientCreate(0, 0)
        if not self._wifi_manager:
            self._client.raise_errno_exception("WiFiManagerClientCreate failed")

    @property
    def saved_networks(self) -> list[WifiSavedNetwork]:
        """Return saved Wi-Fi networks known to the device."""
        result = []

        network_list = self._client.symbols.WiFiManagerClientCopyNetworks(self._wifi_manager).py()
        if not network_list:
            return result

        for network in network_list:
            result.append(WifiSavedNetwork(self._client, self._wifi_manager, network))

        return result

    @property
    def interfaces(self) -> list[str]:
        """Return a list of available Wi-Fi interface names."""
        with self._client.safe_malloc(8) as p_interface:
            if self._client.symbols.Apple80211Open(p_interface):
                self._client.raise_errno_exception("Apple80211Open() failed")

            with self._client.safe_malloc(8) as p_interface_names:
                if self._client.symbols.Apple80211GetIfListCopy(p_interface[0], p_interface_names):
                    self._client.raise_errno_exception("Apple80211GetIfListCopy() failed")

                return p_interface_names[0].py()

    def turn_on(self) -> None:
        """Enable Wi-Fi on the device."""
        self._set(True)

    def turn_off(self) -> None:
        """Disable Wi-Fi on the device."""
        self._set(False)

    def is_on(self) -> bool:
        """Return True if Wi-Fi is enabled."""
        return bool(
            self._client.symbols.WiFiManagerClientCopyProperty(self._wifi_manager, self._client.cf("AllowEnable")).py()
        )

    def get_interface(self, interface_name: Optional[str] = None) -> WifiInterface:
        """Return a bound interface handle for scanning and associating."""
        with self._client.safe_malloc(8) as p_handle:
            if self._client.symbols.Apple80211Open(p_handle):
                self._client.raise_errno_exception("Apple80211Open() failed")
            handle = p_handle[0]

        if interface_name is None:
            wifi_interfaces = self.interfaces

            if not wifi_interfaces:
                raise RpcClientException("no available wifi interfaces were found")

            interface_name = wifi_interfaces[0]

        if self._client.symbols.Apple80211BindToInterface(handle, self._client.cf(interface_name)):
            self._client.raise_errno_exception("Apple80211BindToInterface failed")

        return WifiInterface(self._client, handle)

    def _set(self, is_on: bool) -> None:
        if not self._client.symbols.WiFiManagerClientSetProperty(
            self._wifi_manager, self._client.cf("AllowEnable"), self._client.cf(is_on)
        ):
            raise BadReturnValueError("WiFiManagerClientSetProperty() failed")
