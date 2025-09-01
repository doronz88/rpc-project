import logging

from rpcclient.exceptions import BadReturnValueError


class Backlight:
    def __init__(self, client):
        self._client = client

        BrightnessSystemClient = self._client.symbols.objc_getClass('BrightnessSystemClient')
        if not BrightnessSystemClient:
            logging.error('failed to load BrightnessSystemClient class')
        self._brightness = BrightnessSystemClient.objc_call('new')

    @property
    def brightness(self) -> float:
        """ get brightness value in range: 0.0 - 1.0 """
        return self._brightness.objc_call('copyPropertyForKey:', self._client.cf('DisplayBrightness')).py()['Brightness']

    @brightness.setter
    def brightness(self, value: float):
        """ set brightness in range: 0.0 - 1.0 """
        if not self._brightness.objc_call('setProperty:forKey:', self._client.cf(value),
                                          self._client.cf('DisplayBrightness')):
            raise BadReturnValueError('failed to set DisplayBrightness')
