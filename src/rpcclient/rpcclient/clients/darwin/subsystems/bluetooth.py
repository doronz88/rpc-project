from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient


class Bluetooth(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """bluetooth utils"""

    # bugfix: +[BluetoothManager.setSharedInstanceQueue:] cannot be called twice in the same process,
    # so we use this global to tell if it was already called
    _ENV_QUEUE_SET = "_rpc_server_bluetooth_manager_dispatch_queue_set"

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client
        client.load_framework_lazy("BluetoothManager")

    _bluetooth_manager: DarwinSymbolT_co | None = None

    async def _get_bluetooth_manager(self) -> DarwinSymbolT_co:
        if self._bluetooth_manager is None:
            bluetooth_manager_class = await self._client.symbols.objc_getClass.z("BluetoothManager")
            if not await self._client.getenv.z(self._ENV_QUEUE_SET):
                await bluetooth_manager_class.objc_call.z(
                    "setSharedInstanceQueue:", await self._client.symbols.dispatch_queue_create.z(0, 0)
                )
                await self._client.setenv.z(self._ENV_QUEUE_SET, "1")
            self._bluetooth_manager = await bluetooth_manager_class.objc_call.z("sharedInstance")

        return self._bluetooth_manager

    @zyncio.zmethod
    async def is_on(self) -> bool:
        return await (await self._get_bluetooth_manager()).objc_call.z("enabled") == 1

    @zyncio.zmethod
    async def turn_on(self) -> None:
        await self._set(is_on=1)

    @zyncio.zmethod
    async def turn_off(self) -> None:
        await self._set(is_on=0)

    @zyncio.zproperty
    async def address(self) -> str | None:
        addr = await (await (await self._get_bluetooth_manager()).objc_call.z("localAddress")).py.z()
        assert addr is None or isinstance(addr, str)

    @zyncio.zproperty
    async def connected(self) -> bool:
        return bool(await (await self._get_bluetooth_manager()).objc_call.z("connected"))

    @zyncio.zproperty
    async def _discoverable(self) -> bool:
        return bool(await (await self._get_bluetooth_manager()).objc_call.z("isDiscoverable"))

    @_discoverable.setter
    async def discoverable(self, value: bool) -> None:
        await (await self._get_bluetooth_manager()).objc_call.z("setDiscoverable:", value)

    async def _set(self, is_on) -> None:
        await (await self._get_bluetooth_manager()).objc_call.z("setPowered:", is_on)
        await (await self._get_bluetooth_manager()).objc_call.z("setEnabled:", is_on)

    def __repr__(self):
        if zyncio.is_sync(self):
            return f"<{type(self).__name__} state:{'ON' if self.is_on() else 'OFF'}>"
        return f"<{type(self).__name__} (async)>"
