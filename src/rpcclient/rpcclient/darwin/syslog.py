import datetime

from rpcclient.exceptions import BadReturnValueError


class Syslog:
    """" manage syslog """

    def __init__(self, client):
        self._client = client

    def set_unredacted_logs(self, enable: bool = True):
        """
        enable/disable unredacted logs (allows seeing the <private> strings)
        https://github.com/EthanArbuckle/unredact-private-os_logs
        """
        with self._client.preferences.sc.get_preferences_object(
                '/Library/Preferences/Logging/com.apple.system.logging.plist') as pref:
            pref.set_dict({'Enable-Logging': True, 'Enable-Private-Data': enable})

    def set_har_capture_global(self, enable: bool = True):
        """
        enable/disable HAR logging
        https://github.com/doronz88/harlogger
        """
        if enable:
            self._client.preferences.cf.set('har-capture-global',
                                            self._client.cf(datetime.datetime(9999, 12, 31, 23, 59, 59)),
                                            'com.apple.CFNetwork')
        else:
            self._client.preferences.cf.set('har-capture-global',
                                            self._client.cf(datetime.datetime(1970, 1, 1, 1, 1, 1)),
                                            'com.apple.CFNetwork')

        if self._client.symbols.notify_post('com.apple.CFNetwork.har-capture-update'):
            raise BadReturnValueError('notify_post() failed')
