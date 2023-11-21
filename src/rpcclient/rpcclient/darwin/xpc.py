from datetime import datetime
from functools import lru_cache
from typing import List, Mapping

from rpcclient.darwin.common import CfSerializable
from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.exceptions import MissingLibraryError, RpcXpcSerializationError
from rpcclient.structs.consts import RTLD_NOW


class XPCObject(DarwinSymbol):
    @property
    def type(self) -> int:
        return self._client.symbols.xpc_get_type(self)


class XPCDictionary(XPCObject):
    def set_string(self, key: str, value: str) -> None:
        self._client.symbols.xpc_dictionary_set_string(self, key, value)

    def set_int64(self, key: str, value: int) -> None:
        self._client.symbols.xpc_dictionary_set_int64(self, key, value)

    def set_uint64(self, key: str, value: int) -> None:
        self._client.symbols.xpc_dictionary_set_uint64(self, key, value)

    def set_bool(self, key: str, value: bool) -> None:
        self._client.symbols.xpc_dictionary_set_bool(self, key, value)

    def set_data(self, key: str, value: bytes) -> None:
        self._client.symbols.xpc_dictionary_set_data(self, key, value, len(value))

    def set_fd(self, key: str, value: int) -> None:
        self._client.symbols.xpc_dictionary_set_fd(self, key, value)

    def set_uuid(self, key: str, value: str) -> None:
        self._client.symbols.xpc_dictionary_set_uuid(self, key, value)

    def set_dictionary(self, key: str, value: int) -> None:
        self._client.symbols.xpc_dictionary_set_dictionary(self, key, value)

    def set_object(self, obj: XPCObject) -> None:
        self._client.symbols.xpc_dictionary_set_object(self, obj)

    def set_value(self, obj: XPCObject) -> None:
        self._client.symbols.xpc_dictionary_set_value(self, obj)

    def get_string(self, key: str) -> str:
        return self._client.symbols.xpc_dictionary_get_string(self, key).peek_str()

    def get_int64(self, key: str) -> int:
        return self._client.symbols.xpc_dictionary_get_int64(self, key).c_int64

    def get_uint64(self, key: str) -> int:
        return self._client.symbols.xpc_dictionary_get_uint64(self, key).c_uint64

    def get_bool(self, key: str) -> None:
        return self._client.symbols.xpc_dictionary_get_bool(self, key).c_bool

    def get_data(self, key: str) -> bytes:
        with self._client.safe_malloc(8) as p_length:
            return self._client.symbols.xpc_dictionary_get_data(self, key, p_length).peek(p_length[0])

    def get_fd(self, key: str) -> int:
        return self._client.symbols.xpc_dictionary_get_fd(self, key)

    def get_uuid(self, key: str) -> str:
        return self._client.symbols.xpc_dictionary_get_uuid(self, key).peek_str()

    def get_dictionary(self, key: str) -> 'XPCDictionary':
        return XPCDictionary.create(self._client.symbols.xpc_dictionary_get_dictionary(self, key), self._client)

    def get_object(self, key: str) -> XPCObject:
        return XPCObject.create(self._client.symbols.xpc_dictionary_get_object(self, key), self._client)

    def get_value(self, key: str) -> XPCObject:
        return XPCObject.create(self._client.symbols.xpc_dictionary_get_value(self, key), self._client)


class Xpc:
    def __init__(self, client):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client
        self._load_duet_activity_scheduler_manager()
        self.sharedScheduler = self._client.symbols.objc_getClass('_DASScheduler').objc_call('sharedScheduler')

    def create_xpc_dictionary(self) -> XPCDictionary:
        return XPCDictionary.create(self._client.symbols.xpc_dictionary_create(0, 0, 0), self._client)

    def send_xpc_dictionary(self, service_name: str, message: XPCDictionary) -> XPCDictionary:
        """
        Send a native XPC dictionary to a XPC service synchronously and return result.

        :param service_name: mach service name
        :param message: xpc message to send
        :return: received response
        """
        return XPCDictionary.create(self.send_message_raw(service_name, message), self._client)

    def send_message_using_cf_serialization(
            self, service_name: str, message: CfSerializable, decode_cf: bool = True) -> CfSerializable:
        """
        Send a CFObject serialized over an XPC object to a XPC service synchronously and return reply.

        :param service_name: mach service name
        :param message: xpc message to send
        :param decode_cf: should response be decoded as CFObject-over-XPCObject or a native XPC object
        :return: received response
        """
        message_raw = self.encode_xpc_message_using_cf_serialization(message)
        if message_raw == 0:
            raise RpcXpcSerializationError()
        response = self.send_message_raw(service_name, message_raw)
        if response == 0:
            raise RpcXpcSerializationError()
        return self.decode_xpc_message_using_cf_serialization(
            response) if decode_cf else self.decode_xpc_object_using_cf_serialization(response)

    def send_object_using_cf_serialization(self, service_name: str, message: CfSerializable) -> CfSerializable:
        """
        Send a native XPC object serialized over a CFObject to a XPC service synchronously and return reply.

        :param service_name: mach service name
        :param message: xpc message to send
        :return: received response
        """
        message_raw = self.encode_xpc_object_using_cf_serialization(message)
        if message_raw == 0:
            raise RpcXpcSerializationError()
        response = self.send_message_raw(service_name, message_raw)
        if response == 0:
            raise RpcXpcSerializationError()
        return self.decode_xpc_object_using_cf_serialization(response)

    def decode_xpc_object_using_cf_serialization(self, address: DarwinSymbol) -> CfSerializable:
        """
        Convert XPC object to python object using CF serialization.
        """
        return self._client.symbols._CFXPCCreateCFObjectFromXPCObject(address).py()

    def encode_xpc_object_using_cf_serialization(self, obj: CfSerializable) -> DarwinSymbol:
        """
        Convert python object to XPC object using CF conversion.
        """
        return self._client.symbols._CFXPCCreateXPCObjectFromCFObject(self._client.cf(obj))

    def decode_xpc_message_using_cf_serialization(self, address: DarwinSymbol) -> CfSerializable:
        """
        Convert a CFObject serialized over an XPCObject to python object
        """
        return self._client.symbols._CFXPCCreateCFObjectFromXPCMessage(address).py()

    def encode_xpc_message_using_cf_serialization(self, obj: CfSerializable) -> DarwinSymbol:
        """
        Convert python object to a CFObject serialized over an XPCObject
        """
        return self._client.symbols._CFXPCCreateXPCMessageWithCFObject(self._client.cf(obj))

    def send_message_raw(self, service_name: str, message_raw: DarwinSymbol) -> DarwinSymbol:
        """ Send a RAW xpc object to given service_name and wait reply. """
        conn = self._connect_to_mach_service(service_name)
        return self._client.symbols.xpc_connection_send_message_with_reply_sync(conn, message_raw)

    def force_run_activities(self, activities: List[str]) -> None:
        self.sharedScheduler.objc_call('forceRunActivities:', self._client.cf(activities))

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
