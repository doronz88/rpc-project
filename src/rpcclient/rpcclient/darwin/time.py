from datetime import datetime

from rpcclient.darwin.structs import timeval
from rpcclient.exceptions import MissingLibraryError
from rpcclient.structs.consts import RTLD_NOW


class Time:
    def __init__(self, client):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client
        self._load_core_time_framework()

    def _load_core_time_framework(self):
        if self._client.dlopen('/System/Library/PrivateFrameworks/CoreTime.framework/CoreTime', RTLD_NOW):
            return
        raise MissingLibraryError('failed to load CoreTime')

    def now(self):
        with self._client.safe_calloc(timeval.sizeof()) as current:
            self._client.symbols.gettimeofday(current, 0)
            time_of_day = timeval.parse(current.peek(timeval.sizeof()))
        return datetime.fromtimestamp(time_of_day.tv_sec + (time_of_day.tv_usec / (10 ** 6)))

    def set_current(self, new_time: datetime):
        self._client.symbols.TMSetAutomaticTimeZoneEnabled(0)
        with self._client.safe_calloc(timeval.sizeof()) as current:
            current.poke(timeval.build({'tv_sec': int(new_time.timestamp()), 'tv_usec': new_time.microsecond}))
            self._client.symbols.settimeofday(current, 0)

    def set_auto(self):
        self._client.symbols.TMSetAutomaticTimeZoneEnabled(1)

    @property
    def is_set_automatically(self):
        return bool(self._client.symbols.TMIsAutomaticTimeZoneEnabled())