import ctypes
import logging
from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.common import CfSerializableAny, CfSerializableT
from rpcclient.core._types import ClientBound
from rpcclient.core.allocated import Allocated
from rpcclient.exceptions import BadReturnValueError, RpcClientException
from rpcclient.utils import cached_async_method


if TYPE_CHECKING:
    from rpcclient.clients.ios.client import BaseIosClient

logger = logging.getLogger(__name__)


class WifiSavedNetwork(ClientBound["BaseIosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(
        self, client: "BaseIosClient[DarwinSymbolT_co]", wifi_manager: DarwinSymbolT_co, network: DarwinSymbolT_co
    ) -> None:
        self._client = client
        self._wifi_manager: DarwinSymbolT_co = wifi_manager
        self._network: DarwinSymbolT_co = network

    @zyncio.zproperty
    async def ssid(self) -> bytes:
        """Return the network SSID as raw bytes."""
        return await self.get_property.z("SSID", bytes)

    @zyncio.zproperty
    async def bssid(self) -> str:
        """Return the network BSSID as a string."""
        return await self.get_property.z("BSSID", str)

    @zyncio.zmethod
    async def get_property(
        self, name: str, typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = CfSerializableAny
    ) -> CfSerializableT:
        """Return a WiFiNetwork property by name from the underlying CF object."""
        return await (
            await self._client.symbols.WiFiNetworkGetProperty.z(self._network, await self._client.cf.z(name))
        ).py.z(typ)

    @zyncio.zmethod
    async def forget(self) -> None:
        """Remove this network from the saved networks list."""
        await self._client.symbols.WiFiManagerClientRemoveNetwork.z(self._wifi_manager, self._network)

    def __repr__(self) -> str:
        if zyncio.is_sync(self):
            return f"<{self.__class__.__name__} SSID:{self.ssid} BSSID:{self.bssid}>"
        return f"<{self.__class__.__name__} (async)>"


class WifiScannedNetwork(ClientBound["BaseIosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "BaseIosClient[DarwinSymbolT_co]", interface: DarwinSymbolT_co, network: dict) -> None:
        self._client = client
        self._interface = interface
        self.network = network

    @property
    def ssid(self) -> bytes:
        """Return the scanned network SSID as raw bytes."""
        return self.network["SSID"]

    @property
    def bssid(self) -> str:
        """Return the scanned network BSSID as a string."""
        return self.network["BSSID"]

    @property
    def rssi(self) -> int:
        """Return the received signal strength indicator (RSSI)."""
        return ctypes.c_int64(self.network["RSSI"]).value

    @property
    def channel(self) -> int:
        """Return the Wi-Fi channel number."""
        return self.network["CHANNEL"]

    @zyncio.zmethod
    async def connect(self, password: str | None = None) -> None:
        """Associate to this network, optionally providing a password."""
        result = await self._client.symbols.Apple80211Associate.z(
            self._interface,
            await self._client.cf.z(self.network),
            await self._client.cf.z(password) if password else 0,
        )

        if result:
            raise BadReturnValueError(f"Apple80211Associate() failed with: {result}")

    @zyncio.zmethod
    async def disconnect(self) -> None:
        """Disassociate from the current network."""
        if await self._client.symbols.Apple80211Disassociate.z(self._interface):
            raise BadReturnValueError("Apple80211Disassociate() failed")

    def __repr__(self) -> str:
        if zyncio.is_sync(self):
            return (
                f"<{self.__class__.__name__} "
                f"SSID:{self.ssid} "
                f"BSSID:{self.bssid} "
                f"CHANNEL:{self.channel} "
                f"RSSI:{self.rssi}"
                ">"
            )
        return f"<{self.__class__.__name__} (async)>"


class WifiInterface(Allocated["BaseIosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "BaseIosClient[DarwinSymbolT_co]", interface: DarwinSymbolT_co) -> None:
        super().__init__()
        self._client = client
        self._interface: DarwinSymbolT_co = interface

    @zyncio.zmethod
    async def scan(self, options: dict | None = None) -> list[WifiScannedNetwork[DarwinSymbolT_co]]:
        """Scan for nearby networks and return a list of WifiScannedNetwork."""

        if options is None:
            options = {}

        result = []
        async with self._client.safe_malloc.z(8) as p_found_networks:
            while True:
                scan_result = await self._client.symbols.Apple80211Scan.z(
                    self._interface, p_found_networks, await self._client.cf.z(options)
                )
                if scan_result == 0:
                    break
                elif scan_result == -1:
                    raise BadReturnValueError("Apple80211Scan failed")
                # else, try again

            for network in await (await p_found_networks.getindex(0)).py.z(list):
                result.append(WifiScannedNetwork(self._client, self._interface, network))

        return result

    @zyncio.zmethod
    async def disconnect(self) -> None:
        """Disconnect from the currently associated Wi-Fi network."""
        await self._client.symbols.Apple80211Disassociate.z(self._interface)

    async def _deallocate(self) -> None:
        await self._client.symbols.Apple80211Close.z(self._interface)


class IosWifi(ClientBound["BaseIosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """iOS Wi-Fi utilities backed by WiFiKit and Apple80211."""

    def __init__(self, client: "BaseIosClient[DarwinSymbolT_co]") -> None:
        self._client = client
        self._client.load_framework_lazy("WiFiKit")

    @cached_async_method
    async def _get_wifi_manager(self) -> DarwinSymbolT_co:
        wifi_manager = await self._client.symbols.WiFiManagerClientCreate.z(0, 0)
        if not wifi_manager:
            await self._client.raise_errno_exception.z("WiFiManagerClientCreate failed")
        return wifi_manager

    @zyncio.zproperty
    async def saved_networks(self) -> list[WifiSavedNetwork]:
        """Return saved Wi-Fi networks known to the device."""
        network_list = await (
            await self._client.symbols.WiFiManagerClientCopyNetworks.z(await self._get_wifi_manager())
        ).py.z((list, type(None)))
        if not network_list:
            return []

        return [WifiSavedNetwork(self._client, await self._get_wifi_manager(), network) for network in network_list]

    @zyncio.zproperty
    async def interfaces(self) -> list[str]:
        """Return a list of available Wi-Fi interface names."""
        async with self._client.safe_malloc.z(8) as p_interface:
            if await self._client.symbols.Apple80211Open.z(p_interface):
                await self._client.raise_errno_exception.z("Apple80211Open() failed")

            async with self._client.safe_malloc.z(8) as p_interface_names:
                if await self._client.symbols.Apple80211GetIfListCopy.z(
                    await p_interface.getindex(0), p_interface_names
                ):
                    await self._client.raise_errno_exception.z("Apple80211GetIfListCopy() failed")

                return await (await p_interface_names.getindex(0)).py.z(list)

    @zyncio.zmethod
    async def turn_on(self) -> None:
        """Enable Wi-Fi on the device."""
        await self._set(True)

    @zyncio.zmethod
    async def turn_off(self) -> None:
        """Disable Wi-Fi on the device."""
        await self._set(False)

    @zyncio.zmethod
    async def is_on(self) -> bool:
        """Return True if Wi-Fi is enabled."""
        return bool(
            await (
                await self._client.symbols.WiFiManagerClientCopyProperty.z(
                    await self._get_wifi_manager(), await self._client.cf.z("AllowEnable")
                )
            ).py.z()
        )

    @zyncio.zmethod
    async def get_interface(self, interface_name: str | None = None) -> WifiInterface[DarwinSymbolT_co]:
        """Return a bound interface handle for scanning and associating."""
        async with self._client.safe_malloc.z(8) as p_handle:
            if await self._client.symbols.Apple80211Open.z(p_handle):
                await self._client.raise_errno_exception.z("Apple80211Open() failed")
            handle = await p_handle.getindex(0)

        if interface_name is None:
            wifi_interfaces = await type(self).interfaces(self)

            if not wifi_interfaces:
                raise RpcClientException("no available wifi interfaces were found")

            interface_name = wifi_interfaces[0]

        if await self._client.symbols.Apple80211BindToInterface.z(handle, await self._client.cf.z(interface_name)):
            await self._client.raise_errno_exception.z("Apple80211BindToInterface failed")

        return WifiInterface(self._client, handle)

    async def _set(self, is_on: bool) -> None:
        if not await self._client.symbols.WiFiManagerClientSetProperty.z(
            await self._get_wifi_manager(), await self._client.cf.z("AllowEnable"), await self._client.cf.z(is_on)
        ):
            raise BadReturnValueError("WiFiManagerClientSetProperty() failed")
