from rpcclient.darwin.client import DarwinClient
from rpcclient.macos.bluetooth import Bluetooth


class MacosClient(DarwinClient):

    def __init__(self, sock, sysname: str, hostname: str, port: int = None):
        super().__init__(sock, sysname, hostname, port)

        self.bluetooth = Bluetooth(self)
