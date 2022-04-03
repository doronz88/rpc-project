import threading
from socket import socket

from rpcclient.protocol import protocol_message_t


class ClientConnection:
    def __init__(self, sock):
        self._sock = sock
        self._lock = threading.Lock()

    def send_command(self, command):
        port, listening_socket = self._new_listening_socket()
        with listening_socket:
            message_data = command.serialize()
            message_data.update({'port': port})
            message = protocol_message_t.build(message_data)
            with self._lock:
                self._sock.sendall(message)
            return self._listen_for_response(listening_socket, command.handle_response)

    @staticmethod
    def _new_listening_socket():
        s = socket()
        s.bind(('0.0.0.0', 0))
        address, port = s.getsockname()
        s.listen()
        return port, s

    @staticmethod
    def _listen_for_response(listening_socket, handler):
        incoming_socket, address = listening_socket.accept()
        with incoming_socket:
            return handler(incoming_socket)

    def close(self):
        self._sock.close()
