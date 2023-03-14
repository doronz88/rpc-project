from datetime import datetime
from functools import lru_cache
from typing import List, Mapping

from rpcclient.darwin.common import CfSerializable
from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.exceptions import MissingLibraryError, RpcXpcSerializationError
from rpcclient.structs.consts import RTLD_NOW


class Xpc:
    def __init__(self, client):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client
        self._load_duet_activity_scheduler_manager()
        self.sharedScheduler = self._client.objc_get_class('_DASScheduler').sharedScheduler().objc_symbol

    def send_message(self, service_name: str, message: CfSerializable, decode_cf: bool = True) -> CfSerializable:
        """
        Send a CFObject serialized over an XPC object to a XPC service synchronously and return result.

        :param service_name: mach service name
        :param message: xpc message to send
        :param decode_cf: should response be decoded as CFObject-over-XPCObject or a native XPC object
        :return: received response
        """
        message_raw = self.to_xpc_message(message)
        if message_raw == 0:
            raise RpcXpcSerializationError()
        response = self.send_message_raw(service_name, message_raw)
        if response == 0:
            raise RpcXpcSerializationError()
        return self.from_xpc_message(response) if decode_cf else self.from_xpc_object(response)

    def send_object(self, service_name: str, message: CfSerializable) -> CfSerializable:
        """
        Send a native XPC message to a XPC service synchronously and return result.

        :param service_name: mach service name
        :param message: xpc message to send
        :return: received response
        """
        message_raw = self.to_xpc_object(message)
        if message_raw == 0:
            raise RpcXpcSerializationError()
        response = self.send_message_raw(service_name, message_raw)
        if response == 0:
            raise RpcXpcSerializationError()
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

    def from_xpc_message(self, address: DarwinSymbol) -> CfSerializable:
        """
        Convert a CFObject serialized over an XPCObject to python object
        """
        return self._client.symbols._CFXPCCreateCFObjectFromXPCMessage(address).py()

    def to_xpc_message(self, obj: CfSerializable) -> DarwinSymbol:
        """
        Convert python object to a CFObject serialized over an XPCObject
        """
        return self._client.symbols._CFXPCCreateXPCMessageWithCFObject(self._client.cf(obj))

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
