from typing import Optional

from rpcclient.exceptions import MissingLibraryError
from rpcclient.structs.consts import RTLD_NOW


class Bluetooth:
    """ bluetooth utils """

    # bugfix: +[BluetoothManager.setSharedInstanceQueue:] cannot be called twice in the same process,
    # so we use this global to tell if it was already called
    _ENV_QUEUE_SET = '_rpc_server_bluetooth_manager_dispatch_queue_set'

    def __init__(self, client):
        self._client = client
        self._load_bluetooth_manager()

        bluetooth_manager_class = client.symbols.objc_getClass('BluetoothManager')
        if not client.getenv(self._ENV_QUEUE_SET):
            bluetooth_manager_class.objc_call('setSharedInstanceQueue:',
                                              self._client.symbols.dispatch_queue_create(0, 0))
            client.setenv(self._ENV_QUEUE_SET, '1')
        self._bluetooth_manager = bluetooth_manager_class.objc_call('sharedInstance')

    def is_on(self):
        return 1 == self._bluetooth_manager.objc_call('enabled')

    def turn_on(self):
        self._set(is_on=1)

    def turn_off(self):
        self._set(is_on=0)

    @property
    def address(self) -> Optional[str]:
        return self._bluetooth_manager.objc_call('localAddress').py()

    @property
    def connected(self) -> bool:
        return bool(self._bluetooth_manager.objc_call('connected'))

    @property
    def discoverable(self) -> bool:
        return bool(self._bluetooth_manager.objc_call('isDiscoverable'))

    @discoverable.setter
    def discoverable(self, value: bool):
        self._bluetooth_manager.objc_call('setDiscoverable:', value)

    def _load_bluetooth_manager(self):
        options = [
            '/System/Library/PrivateFrameworks/BluetoothManager.framework/BluetoothManager',
        ]
        for option in options:
            if self._client.dlopen(option, RTLD_NOW):
                return
        raise MissingLibraryError('failed to load BluetoothManager')

    def _set(self, is_on):
        self._bluetooth_manager.objc_call('setPowered:', is_on)
        self._bluetooth_manager.objc_call('setEnabled:', is_on)

    def __repr__(self):
        return f"<Bluetooth state:{'ON' if self.is_on() else 'OFF'}>"
