import logging
import typing
from socket import socket
from typing import Mapping

from construct import Int64sl

from rpcclient.darwin.structs import pid_t, exitcode_t
from rpcclient.exceptions import ServerDiedError, ArgumentError, SpawnError
from rpcclient.protocol import cmd_type_t, reply_protocol_message_t, protocol_message_t, dummy_block_t, exec_chunk_t, \
    exec_chunk_type_t, call_response_t_size, call_response_t

INVALID_PID = 0xffffffff


class RPCCommand:
    def __init__(self, cmd_type: cmd_type_t):
        self._cmd_type = cmd_type

    def serialize(self) -> Mapping:
        return {"cmd_type": self._cmd_type}

    def handle_response(self, server_socket: socket):
        raise NotImplementedError()

    @staticmethod
    def _recvall(server_socket: socket, size: int) -> bytes:
        buf = b''
        while size:
            try:
                chunk = server_socket.recv(size)
            except BlockingIOError:
                continue
            if server_socket.gettimeout() == 0 and not chunk:
                # TODO: replace self._sock.gettimeout() == 0 on -> self._sock.getblocking() on python37+
                raise ServerDiedError()
            size -= len(chunk)
            buf += chunk
        return buf


class RPCDlopenCommand(RPCCommand):
    def __init__(self, filename: str, mode: int):
        super(RPCDlopenCommand, self).__init__(cmd_type_t.CMD_DLOPEN)
        self._filename = filename
        self._mode = mode

    def serialize(self) -> Mapping:
        serialized_command = super(RPCDlopenCommand, self).serialize()
        serialized_command.update({'data': {'filename': self._filename, 'mode': self._mode}})
        return serialized_command

    def handle_response(self, server_socket):
        return Int64sl.parse(self._recvall(server_socket, Int64sl.sizeof()))


class RPCDlsymCommand(RPCCommand):
    def __init__(self, lib: int, symbol_name: str):
        super(RPCDlsymCommand, self).__init__(cmd_type_t.CMD_DLSYM)
        self._lib = lib
        self._symbol_name = symbol_name

    def serialize(self) -> Mapping:
        serialized_command = super(RPCDlsymCommand, self).serialize()
        serialized_command.update({'data': {'lib': self._lib, 'symbol_name': self._symbol_name}})
        return serialized_command

    def handle_response(self, server_socket):
        return Int64sl.parse(self._recvall(server_socket, Int64sl.sizeof()))


class RPCDlcloseCommand(RPCCommand):
    def __init__(self, lib: int):
        super(RPCDlcloseCommand, self).__init__(cmd_type_t.CMD_DLCLOSE)
        self._lib = lib

    def serialize(self) -> Mapping:
        serialized_command = super(RPCDlcloseCommand, self).serialize()
        serialized_command.update({'data': {'lib': self._lib}})
        return serialized_command

    def handle_response(self, server_socket):
        return Int64sl.parse(self._recvall(server_socket, Int64sl.sizeof()))


class RPCPeekCommand(RPCCommand):
    def __init__(self, address: int, size: int):
        super(RPCPeekCommand, self).__init__(cmd_type_t.CMD_PEEK)
        self._address = address
        self._size = size

    def serialize(self) -> Mapping:
        serialized_command = super(RPCPeekCommand, self).serialize()
        serialized_command.update({'data': {'address': self._address, 'size': self._size}})
        return serialized_command

    def handle_response(self, server_socket):
        reply = reply_protocol_message_t.parse(self._recvall(server_socket, reply_protocol_message_t.sizeof()))
        if reply.cmd_type == cmd_type_t.CMD_REPLY_ERROR:
            raise ArgumentError(f'failed to read {self._size} bytes from {self._address}')
        return self._recvall(server_socket, self._size)


class RPCPokeCommand(RPCCommand):
    def __init__(self, address: int, data: bytes):
        super(RPCPokeCommand, self).__init__(cmd_type_t.CMD_POKE)
        self._address = address
        self._data = data

    def serialize(self) -> Mapping:
        serialized_command = super(RPCPokeCommand, self).serialize()
        serialized_command.update({'data': {'address': self._address, 'size': len(self._data), 'data': self._data}})
        return serialized_command

    def handle_response(self, server_socket):
        reply = reply_protocol_message_t.parse(self._recvall(server_socket, reply_protocol_message_t.sizeof()))
        if reply.cmd_type == cmd_type_t.CMD_REPLY_ERROR:
            raise ArgumentError(f'failed to write {len(self._data)} bytes to {self._address}')


class RPCGetDummyBlockCommand(RPCCommand):
    def __init__(self):
        super(RPCGetDummyBlockCommand, self).__init__(cmd_type_t.CMD_GET_DUMMY_BLOCK)

    def serialize(self) -> Mapping:
        serialized_command = super(RPCGetDummyBlockCommand, self).serialize()
        serialized_command.update({'data': None})
        return serialized_command

    def handle_response(self, server_socket):
        return dummy_block_t.parse(self._recvall(server_socket, dummy_block_t.sizeof()))


class RPCCallCommand(RPCCommand):

    def __init__(self, address, argv):
        super(RPCCallCommand, self).__init__(cmd_type_t.CMD_CALL)
        self._address = address
        self._argv = argv

    def serialize(self) -> Mapping:
        serialized_command = super(RPCCallCommand, self).serialize()
        serialized_command.update({'data': {'address': self._address, 'argv': self._argv}})
        return serialized_command

    def handle_response(self, server_socket):
        return call_response_t.parse(self._recvall(server_socket, call_response_t_size))


class RPCExecuteCommand(RPCCommand):

    def __init__(self, argv: typing.List[str], envp: typing.List[str], background=False,
                 execution_loop_function=None, pre_rw_execution_loop=None, post_rw_execution_loop=None):
        super(RPCExecuteCommand, self).__init__(cmd_type_t.CMD_EXEC)
        self._argv = argv
        self._envp = envp
        self._background = background
        self._execution_loop_function = execution_loop_function
        self._pre_rw_execution_loop = pre_rw_execution_loop
        self._post_rw_execution_loop = post_rw_execution_loop

    def serialize(self) -> Mapping:
        serialized_command = super(RPCExecuteCommand, self).serialize()
        serialized_command.update({'data': {'background': self._background, 'argv': self._argv, 'envp': self._envp}})
        return serialized_command

    def handle_response(self, server_socket):
        pid = pid_t.parse(self._recvall(server_socket, pid_t.sizeof()))
        if pid == INVALID_PID:
            raise SpawnError(f'failed to spawn: {self._argv}')

        logging.info(f'shell process started as pid: {pid}')

        if self._background:
            return pid, None

        if self._pre_rw_execution_loop is not None:
            self._pre_rw_execution_loop()

        def _read_chunk_from_socket():
            buf = self._recvall(server_socket, exec_chunk_t.sizeof())
            exec_chunk = exec_chunk_t.parse(buf)
            data = self._recvall(server_socket, exec_chunk.size)
            if exec_chunk.chunk_type == exec_chunk_type_t.CMD_EXEC_CHUNK_TYPE_STDOUT:
                return data.decode(), None
            elif exec_chunk.chunk_type == exec_chunk_type_t.CMD_EXEC_CHUNK_TYPE_ERRORCODE:
                return None, exitcode_t.parse(data)

        def _send_data_to_socket(data):
            server_socket.sendall(data)

        try:
            # the socket must be non-blocking for using select()
            server_socket.setblocking(False)
            error = self._execution_loop_function(server_socket, _read_chunk_from_socket, _send_data_to_socket)
        except Exception:  # noqa: E722
            server_socket.setblocking(True)
            # this is important to really catch every exception here, even exceptions not inheriting from Exception
            # so the controlling terminal will remain working with its previous settings
            if self._post_rw_execution_loop is not None:
                self._post_rw_execution_loop()
            raise

        if self._post_rw_execution_loop is not None:
            self._post_rw_execution_loop()

        return pid, error
