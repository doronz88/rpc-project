from collections import namedtuple

from rpcclient.clients.darwin.symbol import DarwinSymbol

CGRect = namedtuple('CGRect', 'x0 y0 x1 y1')


class ScreenCapture:
    """ monitor screen events """

    def __init__(self, client):
        self._client = client

    @property
    def main_display(self) -> DarwinSymbol:
        return self._client.symbols.objc_getClass('CADisplay').objc_call('mainDisplay')

    @property
    def bounds(self) -> CGRect:
        result = self.main_display.objc_call('bounds', return_raw=True)
        return CGRect(x0=result.d0, y0=result.d1, x1=result.d2, y1=result.d3)

    @property
    def screenshot(self) -> bytes:
        return self._client.symbols.UIImagePNGRepresentation(self._client.symbols._UICreateScreenUIImage()).py()
