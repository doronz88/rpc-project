from datetime import datetime
from functools import lru_cache
from typing import List, Mapping

from rpcclient.darwin.common import CfSerializable
from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.exceptions import MissingLibraryError
from rpcclient.structs.consts import RTLD_NOW


class Xpc:
    def __init__(self, client):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client
        self._load_duet_activity_scheduler_manager()
        self.sharedScheduler = self._client.objc_get_class('_DASScheduler').sharedScheduler().objc_symbol

    def send_message(self, service_name: str, message: CfSerializable) -> CfSerializable:
        """
        Send message to a service and return result.
        """
        message_raw = self.to_xpc_object(message)
        assert message_raw != 0
        response = self.send_message_raw(service_name, message_raw)
        assert response != 0
        return self.from_xpc_object(response)

    def from_xpc_object(self, address: DarwinSymbol) -> CfSerializable:
        """
        Convert XPC object to python object.
        """
        return self._client.symbols._CFXPCCreateCFObjectFromXPCObject(address).py()

    def to_xpc_object(self, obj: CfSerializable) -> DarwinSymbol:
        """
        Convert python object to XPC object.
        """
        return self._client.symbols._CFXPCCreateXPCObjectFromCFObject(self._client.cf(obj))

    def send_message_raw(self, service_name, message_raw) -> DarwinSymbol:
        conn = self._connect_to_mach_service(service_name)
        return self._client.symbols.xpc_connection_send_message_with_reply_sync(conn, message_raw)

    def force_run_activities(self, activities: List[str]) -> None:
        self.sharedScheduler.forceRunActivities_(self._client.cf(activities))

    @property
    def loaded_activities(self) -> Mapping:
        return self._client.preferences.cf.get_dict('com.apple.xpc.activity2', 'root')

    def set_activity_base_date(self, name: str, date: datetime) -> None:
        activity_base_dates = self.loaded_activities['ActivityBaseDates']
        activity_base_dates[name] = date
        self._client.preferences.cf.set('ActivityBaseDates', activity_base_dates, 'com.apple.xpc.activity2', 'root')

    @lru_cache(maxsize=None)
    def _connect_to_mach_service(self, service_name) -> DarwinSymbol:
        conn = self._client.symbols.xpc_connection_create_mach_service(service_name, 0, 0)
        assert conn != 0, 'failed to create xpc connection'
        self._client.symbols.xpc_connection_set_event_handler(conn, self._client.get_dummy_block())
        self._client.symbols.xpc_connection_resume(conn)
        return conn

    def _load_duet_activity_scheduler_manager(self) -> None:
        options = [
            '/System/Library/PrivateFrameworks/DuetActivityScheduler.framework/DuetActivityScheduler',
        ]
        for option in options:
            if self._client.dlopen(option, RTLD_NOW):
                return
        raise MissingLibraryError('failed to load DuetActivityScheduler')
