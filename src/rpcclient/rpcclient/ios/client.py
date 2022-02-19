import typing

from rpcclient.darwin.client import DarwinClient


class IosClient(DarwinClient):
    @property
    def roots(self) -> typing.List[str]:
        """ get a list of all accessible darwin roots when used for lookup of files/preferences/... """
        return super().roots + ['/var/mobile']
