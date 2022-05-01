from functools import lru_cache


class Xpc:
    def __init__(self, client):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client

    def send_message(self, service_name, message):
        """
        Send message to a service and return result.
        """
        message_raw = self.to_xpc_object(message)
        assert message_raw != 0
        response = self.send_message_raw(service_name, message_raw)
        assert response != 0
        return self.from_xpc_object(response)

    def from_xpc_object(self, address):
        """
        Convert XPC object to python object.
        """
        return self._client.symbols._CFXPCCreateCFObjectFromXPCObject(address).py()

    def to_xpc_object(self, obj):
        """
        Convert python object to XPC object.
        """
        return self._client.symbols._CFXPCCreateXPCObjectFromCFObject(self._client.cf(obj))

    def send_message_raw(self, service_name, message_raw):
        conn = self._connect_to_mach_service(service_name)
        return self._client.symbols.xpc_connection_send_message_with_reply_sync(conn, message_raw)

    @lru_cache(maxsize=None)
    def _connect_to_mach_service(self, service_name):
        conn = self._client.symbols.xpc_connection_create_mach_service(service_name, 0, 0)
        assert conn != 0, 'failed to create xpc connection'
        self._client.symbols.xpc_connection_set_event_handler(conn, self._client.get_dummy_block())
        self._client.symbols.xpc_connection_resume(conn)
        return conn
