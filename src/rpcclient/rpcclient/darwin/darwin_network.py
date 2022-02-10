from collections import namedtuple
from typing import List

from rpcclient.exceptions import RpcClientException
from rpcclient.network import Network

WifiNetwork = namedtuple('WifiNetwork', 'ssid bssid rssi')


class DarwinNetwork(Network):
    def __init__(self, client):
        super().__init__(client)

        if 0 == client.dlopen('/System/Library/Frameworks/CoreWLAN.framework/Versions/A/CoreWLAN', 2):
            raise RpcClientException('failed to load CoreWLAN')

    def scan(self, iface: str) -> List[WifiNetwork]:
        """ perform wifi scan on selected interface """
        result = []
        CWInterface = self._client.symbols.objc_getClass('CWInterface')
        iface = CWInterface.objc_call('alloc').objc_call('initWithInterfaceName:', self._client.cf(iface))
        networks = iface.objc_call('scanForNetworksWithName:error:', 0, 0).objc_call('allObjects')

        for i in range(networks.objc_call('count')):
            network = networks.objc_call('objectAtIndex:', i)
            result.append(WifiNetwork(ssid=network.objc_call('ssidData').py, bssid=network.objc_call('bssid').py,
                                      rssi=network.objc_call('rssiValue').c_int64))

        return result
