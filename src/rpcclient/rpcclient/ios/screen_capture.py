import dataclasses

from rpcclient.darwin.symbol import DarwinSymbol
from vncserver import VNCServer


@dataclasses.dataclass
class CGPoint:
    x: float
    y: float


@dataclasses.dataclass
class CGSize:
    width: float
    height: float

    @property
    def size(self):
        return self.width * self.height


@dataclasses.dataclass
class CGRect:
    origin: CGPoint
    size: CGSize


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
        return CGRect(origin=CGPoint(x=d[0], y=d[1]), size=CGSize(width=d[2], height=d[3]))

    def get_screenshot(self, size=None) -> bytes:
        image = self._client.symbols._UICreateScreenUIImage()
        if size:
            self._client.symbols.UIGraphicsBeginImageContext(size[0], size[1])
            image.objc_call('drawInRect:', 0.0, 0.0, size[0], size[1])
            image = self._client.symbols.UIGraphicsGetImageFromCurrentImageContext()
            self._client.symbols.UIGraphicsEndImageContext()
        return self._client.symbols.UIImagePNGRepresentation(image).py

    def vnc_server(self, port=9999):
        VNCServer(self._client, port=port).start()
