from datetime import datetime
from typing import TYPE_CHECKING, Any, Generic
from uuid import UUID

import zyncio
from construct import Container

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.common import CfSerializable
from rpcclient.clients.darwin.consts import XPC_ARRAY_APPEND
from rpcclient.core._types import ClientBound
from rpcclient.core.symbol import AbstractSymbol
from rpcclient.exceptions import BadReturnValueError, RpcXpcSerializationError


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient


class XPCObject(AbstractSymbol, ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, value: int, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client
        self._sym: DarwinSymbolT_co = client.symbol(value)

    def _symbol_from_value(self, value: int) -> DarwinSymbolT_co:
        return self._client.symbol(value)

    @zyncio.zmethod
    async def peek(self, count: int, offset: int = 0) -> bytes:
        return await self._sym.peek.z(count, offset)

    @zyncio.zmethod
    async def poke(self, buf: bytes, offset: int = 0) -> Any:
        return await self._sym.poke.z(buf, offset)

    @zyncio.zmethod
    async def peek_str(self, encoding="utf-8") -> str:
        """peek string at given address"""
        return await self._sym.peek_str.z(encoding=encoding)

    @property
    def arch(self) -> object:
        return self._client.arch

    @property
    def endianness(self) -> str:
        return self._client._endianness

    @zyncio.zmethod
    async def get_dl_info(self) -> Container:
        return await self._sym.get_dl_info.z()

    @zyncio.zproperty
    async def type(self) -> int:
        return await self._client.symbols.xpc_get_type.z(self)


class XPCArray(XPCObject[DarwinSymbolT_co]):
    @zyncio.zmethod
    async def set_data(self, buf: bytes, index: int = XPC_ARRAY_APPEND) -> None:
        """
        See https://developer.apple.com/documentation/xpc/1505937-xpc_array_set_data?language=objc
        """
        await self._client.symbols.xpc_array_set_data.z(self, index, buf, len(buf))


class XPCDictionary(XPCObject[DarwinSymbolT_co]):
    @zyncio.zmethod
    async def set_string(self, key: str, value: str) -> None:
        await self._client.symbols.xpc_dictionary_set_string.z(self, key, value)

    @zyncio.zmethod
    async def set_int64(self, key: str, value: int) -> None:
        await self._client.symbols.xpc_dictionary_set_int64.z(self, key, value)

    @zyncio.zmethod
    async def set_uint64(self, key: str, value: int) -> None:
        await self._client.symbols.xpc_dictionary_set_uint64.z(self, key, value)

    @zyncio.zmethod
    async def set_bool(self, key: str, value: bool) -> None:
        await self._client.symbols.xpc_dictionary_set_bool.z(self, key, value)

    @zyncio.zmethod
    async def set_data(self, key: str, value: bytes) -> None:
        await self._client.symbols.xpc_dictionary_set_data.z(self, key, value, len(value))

    @zyncio.zmethod
    async def set_fd(self, key: str, value: int) -> None:
        await self._client.symbols.xpc_dictionary_set_fd.z(self, key, value)

    @zyncio.zmethod
    async def set_uuid(self, key: str, value: UUID) -> None:
        await self._client.symbols.xpc_dictionary_set_uuid.z(self, key, value.bytes)

    @zyncio.zmethod
    async def set_dictionary(self, key: str, value: int) -> None:
        await self._client.symbols.xpc_dictionary_set_dictionary.z(self, key, value)

    @zyncio.zmethod
    async def set_object(self, obj: XPCObject) -> None:
        await self._client.symbols.xpc_dictionary_set_object.z(self, obj)

    @zyncio.zmethod
    async def set_value(self, key: str, obj: XPCObject) -> None:
        await self._client.symbols.xpc_dictionary_set_value.z(self, key, obj)

    @zyncio.zmethod
    async def get_string(self, key: str) -> str:
        return await (await self._client.symbols.xpc_dictionary_get_string.z(self, key)).peek_str.z()

    @zyncio.zmethod
    async def get_int64(self, key: str) -> int:
        return (await self._client.symbols.xpc_dictionary_get_int64.z(self, key)).c_int64

    @zyncio.zmethod
    async def get_uint64(self, key: str) -> int:
        return (await self._client.symbols.xpc_dictionary_get_uint64.z(self, key)).c_uint64

    @zyncio.zmethod
    async def get_bool(self, key: str) -> bool:
        return (await self._client.symbols.xpc_dictionary_get_bool.z(self, key)).c_bool

    @zyncio.zmethod
    async def get_data(self, key: str) -> bytes:
        async with self._client.safe_malloc.z(8) as p_length:
            return await (await self._client.symbols.xpc_dictionary_get_data.z(self, key, p_length)).peek.z(
                await p_length.getindex(0)
            )

    @zyncio.zmethod
    async def get_fd(self, key: str) -> int:
        return await self._client.symbols.xpc_dictionary_get_fd.z(self, key)

    @zyncio.zmethod
    async def get_uuid(self, key: str) -> str:
        return await (await self._client.symbols.xpc_dictionary_get_uuid.z(self, key)).peek_str.z()

    @zyncio.zmethod
    async def get_dictionary(self, key: str) -> "XPCDictionary":
        return XPCDictionary(await self._client.symbols.xpc_dictionary_get_dictionary.z(self, key), self._client)

    @zyncio.zmethod
    async def get_object(self, key: str) -> XPCObject:
        return XPCObject(await self._client.symbols.xpc_dictionary_get_object.z(self, key), self._client)

    @zyncio.zmethod
    async def get_value(self, key: str) -> XPCObject:
        return XPCObject(await self._client.symbols.xpc_dictionary_get_value.z(self, key), self._client)


class Xpc(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client
        self._client.load_framework_lazy("DuetActivityScheduler")
        self._service_cache: dict[str, DarwinSymbolT_co] = {}

    @zyncio.zproperty
    async def sharedScheduler(self) -> DarwinSymbolT_co:
        return await (await self._client.symbols.objc_getClass.z("_DASScheduler")).objc_call.z("sharedScheduler")

    @zyncio.zmethod
    async def create_xpc_dictionary(self) -> XPCDictionary:
        return XPCDictionary(await self._client.symbols.xpc_dictionary_create.z(0, 0, 0), self._client)

    @zyncio.zmethod
    async def create_xpc_array(self) -> XPCArray:
        return XPCArray(await self._client.symbols.xpc_array_create_empty.z(), self._client)

    @zyncio.zmethod
    async def send_xpc_dictionary(self, service_name: str, message: XPCDictionary) -> XPCDictionary:
        """
        Send a native XPC dictionary to a XPC service synchronously and return result.

        :param service_name: mach service name
        :param message: xpc message to send
        :return: received response
        """
        return XPCDictionary(await self.send_message_raw.z(service_name, message), self._client)

    @zyncio.zmethod
    async def send_message_using_cf_serialization(
        self, service_name: str, message: CfSerializable, decode_cf: bool = True
    ) -> CfSerializable:
        """
        Send a CFObject serialized over an XPC object to a XPC service synchronously and return reply.

        :param service_name: mach service name
        :param message: xpc message to send
        :param decode_cf: should response be decoded as CFObject-over-XPCObject or a native XPC object
        :return: received response
        """
        message_raw = await self.encode_xpc_message_using_cf_serialization.z(message)
        if message_raw == 0:
            raise RpcXpcSerializationError
        response = await self.send_message_raw.z(service_name, message_raw)
        if response == 0:
            raise RpcXpcSerializationError
        return (
            await self.decode_xpc_message_using_cf_serialization.z(response)
            if decode_cf
            else await self.decode_xpc_object_using_cf_serialization.z(response)
        )

    @zyncio.zmethod
    async def send_object_using_cf_serialization(self, service_name: str, message: CfSerializable) -> CfSerializable:
        """
        Send a native XPC object serialized over a CFObject to a XPC service synchronously and return reply.

        :param service_name: mach service name
        :param message: xpc message to send
        :return: received response
        """
        message_raw = await self.encode_xpc_object_using_cf_serialization.z(message)
        if message_raw == 0:
            raise RpcXpcSerializationError()
        response = await self.send_message_raw.z(service_name, message_raw)
        if response == 0:
            raise RpcXpcSerializationError()
        return await self.decode_xpc_object_using_cf_serialization.z(response)

    @zyncio.zmethod
    async def decode_xpc_object_using_cf_serialization(self, address: int) -> CfSerializable:
        """
        Convert XPC object to python object using CF serialization.
        """
        return await (await self._client.symbols._CFXPCCreateCFObjectFromXPCObject.z(address)).py.z()

    @zyncio.zmethod
    async def encode_xpc_object_using_cf_serialization(self, obj: CfSerializable) -> DarwinSymbolT_co:
        """
        Convert python object to XPC object using CF conversion.
        """
        return await self._client.symbols._CFXPCCreateXPCObjectFromCFObject.z(await self._client.cf.z(obj))

    @zyncio.zmethod
    async def decode_xpc_message_using_cf_serialization(self, address: int) -> CfSerializable:
        """
        Convert a CFObject serialized over an XPCObject to python object
        """
        return await (await self._client.symbols._CFXPCCreateCFObjectFromXPCMessage.z(address)).py.z()

    @zyncio.zmethod
    async def encode_xpc_message_using_cf_serialization(self, obj: CfSerializable) -> DarwinSymbolT_co:
        """
        Convert python object to a CFObject serialized over an XPCObject
        """
        return await self._client.symbols._CFXPCCreateXPCMessageWithCFObject.z(await self._client.cf.z(obj))

    @zyncio.zmethod
    async def send_message_raw(self, service_name: str, message_raw: int) -> DarwinSymbolT_co:
        """Send a RAW xpc object to given service_name and wait reply."""
        conn = await self._connect_to_mach_service(service_name)
        return await self._client.symbols.xpc_connection_send_message_with_reply_sync.z(conn, message_raw)

    @zyncio.zmethod
    async def force_run_activities(self, activities: list[str]) -> None:
        await (await type(self).sharedScheduler(self)).objc_call.z(
            "forceRunActivities:", await self._client.cf.z(activities)
        )

    @zyncio.zproperty
    async def loaded_activities(self) -> dict:
        return await self._client.preferences.cf.get_dict.z("com.apple.xpc.activity2", "root")

    @zyncio.zmethod
    async def set_activity_base_date(self, name: str, date: datetime) -> None:
        activity_base_dates = (await type(self).loaded_activities(self))["ActivityBaseDates"]
        activity_base_dates[name] = date
        await self._client.preferences.cf.set.z(
            "ActivityBaseDates", activity_base_dates, "com.apple.xpc.activity2", "root"
        )

    async def _connect_to_mach_service(self, service_name: str) -> DarwinSymbolT_co:
        if service_name not in self._service_cache:
            conn = await self._client.symbols.xpc_connection_create_mach_service.z(service_name, 0, 0)
            if conn == 0:
                raise BadReturnValueError("failed to create xpc connection")
            await self._client.symbols.xpc_connection_set_event_handler.z(conn, await self._client.get_dummy_block.z())
            await self._client.symbols.xpc_connection_resume.z(conn)
            self._service_cache[service_name] = conn

        return self._service_cache[service_name]
