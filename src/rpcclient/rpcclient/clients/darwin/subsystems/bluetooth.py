from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient


class Bluetooth(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """bluetooth utils"""

    # bugfix: +[BluetoothManager.setSharedInstanceQueue:] cannot be called twice in the same process,
    # so we use this global to tell if it was already called
    _ENV_QUEUE_SET = "_rpc_server_bluetooth_manager_dispatch_queue_set"

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client
        client.load_framework_lazy("BluetoothManager")

    _bluetooth_manager: DarwinSymbolT_co | None = None

    async def _get_bluetooth_manager(self) -> DarwinSymbolT_co:
        if self._bluetooth_manager is None:
            bluetooth_manager_class = await self._client.symbols.objc_getClass("BluetoothManager")
            if not await self._client.getenv(self._ENV_QUEUE_SET):
                await bluetooth_manager_class.objc_call(
                    "setSharedInstanceQueue:", await self._client.symbols.dispatch_queue_create(0, 0)
                )
                await self._client.setenv(self._ENV_QUEUE_SET, "1")
            self._bluetooth_manager = await bluetooth_manager_class.objc_call("sharedInstance")

        return self._bluetooth_manager

    async def is_on(self) -> bool:
        return await (await self._get_bluetooth_manager()).objc_call("enabled") == 1

    async def turn_on(self) -> None:
        await self._set(is_on=1)

    async def turn_off(self) -> None:
        await self._set(is_on=0)

    async def address(self) -> str | None:
        addr = await (await (await self._get_bluetooth_manager()).objc_call("localAddress")).py()
        assert addr is None or isinstance(addr, str)

    async def connected(self) -> bool:
        return bool(await (await self._get_bluetooth_manager()).objc_call("connected"))

    async def get_discoverable(self) -> bool:
        return bool(await (await self._get_bluetooth_manager()).objc_call("isDiscoverable"))

    async def set_discoverable(self, value: bool) -> None:
        await (await self._get_bluetooth_manager()).objc_call("setDiscoverable:", value)

    async def _set(self, is_on) -> None:
        await (await self._get_bluetooth_manager()).objc_call("setPowered:", is_on)
        await (await self._get_bluetooth_manager()).objc_call("setEnabled:", is_on)

    def __repr__(self):
        return f"<{type(self).__name__} (async)>"
