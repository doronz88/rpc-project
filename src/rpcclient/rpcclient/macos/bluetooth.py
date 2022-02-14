

class Bluetooth:

    def __init__(self, client):
        self._client = client

    def _set(self, is_on):
        self._client.symbols.IOBluetoothPreferenceSetControllerPowerState(is_on)

    def is_on(self):
        return 1 == self._client.symbols.IOBluetoothPreferenceGetControllerPowerState().c_int64

    def turn_on(self):
        self._set(is_on=1)

    def turn_off(self):
        self._set(is_on=0)

    def __repr__(self):
        return f"<Bluetooth state:{'ON' if self.is_on() else 'OFF'}>"
