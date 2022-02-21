import typing

from rpcclient.darwin.client import DarwinClient
from rpcclient.ios.backlight import Backlight


class IosClient(DarwinClient):
    def __init__(self, sock, sysname: str, hostname: str, port: int = None):
        super().__init__(sock, sysname, hostname, port)
        self.backlight = Backlight(self)

    @property
    def roots(self) -> typing.List[str]:
        """ get a list of all accessible darwin roots when used for lookup of files/preferences/... """
        return super().roots + ['/var/mobile']
