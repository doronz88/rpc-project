from collections import namedtuple

from rpcclient.darwin.symbol import DarwinSymbol

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
        d = self.main_display.objc_call('bounds', return_raw=True).d
        return CGRect(x0=d[0], y0=d[1], x1=d[2], y1=d[3])

    @property
    def screenshot(self) -> bytes:
        return self._client.symbols.UIImagePNGRepresentation(self._client.symbols._UICreateScreenUIImage()).py()
