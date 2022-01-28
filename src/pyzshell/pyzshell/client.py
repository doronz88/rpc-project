import ast
import atexit
import builtins
import contextlib
import logging
import os
import sys
import termios
import typing
from functools import partial
from select import select
from socket import socket

import IPython
from construct import Int64sl
from traitlets.config import Config

from pyzshell.command import CommandsMeta
from pyzshell.exceptions import ArgumentError, SymbolAbsentError
from pyzshell.protocol import protocol_message_t, cmd_type_t, pid_t, exec_chunk_t, exec_chunk_type_t, exitcode_t, fd_t
from pyzshell.structs import utsname_linux, utsname_darwin
from pyzshell.symbol import Symbol
from pyzshell.symbols_jar import SymbolsJar

DEFAULT_PORT = 5910
CHUNK_SIZE = 1024


class Client(metaclass=CommandsMeta):
    DEFAULT_ARGV = ['/bin/sh']

    def __init__(self, hostname: str, port: int = None):
        self._hostname = hostname
        self._port = port
        self._sock = None
        self._old_settings = None
        self._reconnect()
        self.symbols = SymbolsJar.create(self)

    @contextlib.contextmanager
    def safe_malloc(self, size: int):
        x = self.symbols.malloc(size)
        try:
            yield x
        finally:
            self.symbols.free(x)

    @property
    def os_family(self):
        with self.safe_malloc(1024 * 20) as block:
            assert 0 == self.symbols.uname(block)
            return block.peek_str().lower().decode()

    @property
    def uname(self):
        utsname = utsname_linux
        if self.os_family == 'darwin':
            utsname = utsname_darwin
        with self.safe_malloc(utsname.sizeof()) as uname:
            assert 0 == self.symbols.uname(uname)
            return utsname.parse(uname.peek(utsname.sizeof()))

    def info(self):
        uname = self.uname
        print('sysname:', uname.sysname)
        print('nodename:', uname.nodename)
        print('release:', uname.release)
        print('version:', uname.version)
        print('machine:', uname.machine)

    def open(self, filename: str, mode: int):
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_OPEN,
            'data': {'filename': filename, 'mode': mode},
        })
        self._sock.sendall(message)
        fd = fd_t.parse(self._recvall(fd_t.sizeof()))
        return fd

    def close(self, fd: int) -> int:
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_CLOSE,
            'data': {'fd': fd},
        })
        self._sock.sendall(message)
        err = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        return err

    def read(self, fd: int, size: int = CHUNK_SIZE):
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_READ,
            'data': {'fd': fd, 'size': size},
        })
        self._sock.sendall(message)
        err = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        buf = b''
        if err > 0:
            buf = self._recvall(err)
        return err, buf

    def write(self, fd: int, buf: bytes) -> int:
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_WRITE,
            'data': {'fd': fd, 'size': len(buf), 'data': buf},
        })
        self._sock.sendall(message)
        err = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        return err

    def mkdir(self, filename: str, mode: int) -> int:
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_MKDIR,
            'data': {'filename': filename, 'mode': mode},
        })
        self._sock.sendall(message)
        err = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        return err

    def remove(self, filename: str) -> int:
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_REMOVE,
            'data': {'filename': filename},
        })
        self._sock.sendall(message)
        err = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        return err

    def chmod(self, filename: str, mode: int) -> int:
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_CHMOD,
            'data': {'filename': filename, 'mode': mode},
        })
        self._sock.sendall(message)
        err = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        return err

    def dlopen(self, filename: str, mode: int):
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_DLOPEN,
            'data': {'filename': filename, 'mode': mode},
        })
        self._sock.sendall(message)
        err = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        return self.symbol(err)

    def dlclose(self, lib: int):
        lib &= 0xffffffffffffffff
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_DLCLOSE,
            'data': {'lib': lib},
        })
        self._sock.sendall(message)
        err = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        return err

    def dlsym(self, lib: int, symbol_name: str):
        lib &= 0xffffffffffffffff
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_DLSYM,
            'data': {'lib': lib, 'symbol_name': symbol_name},
        })
        self._sock.sendall(message)
        err = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        return err

    def call(self, address: int, argv: typing.List[int] = None):
        fixed_argv = []
        free_list = []

        for arg in argv:
            tmp = arg

            if isinstance(arg, str):
                tmp = self.symbols.malloc(len(arg) + 1)
                tmp.poke(arg.encode() + b'\0')
                free_list.append(tmp)

            elif isinstance(arg, bytes):
                tmp = self.symbols.malloc(len(arg))
                tmp.poke(arg)
                free_list.append(tmp)

            elif isinstance(arg, int) or isinstance(arg, Symbol):
                pass

            else:
                raise ArgumentError(f'invalid parameter type: {arg}')

            tmp &= 0xffffffffffffffff

            fixed_argv.append(tmp)

        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_CALL,
            'data': {'address': address, 'argv': fixed_argv},
        })
        self._sock.sendall(message)
        err = Int64sl.parse(self._recvall(Int64sl.sizeof()))

        for f in free_list:
            self.symbols.free(f)

        return self.symbol(err)

    def peek(self, address: int, size: int) -> bytes:
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_PEEK,
            'data': {'address': address, 'size': size},
        })
        self._sock.sendall(message)
        return self._recvall(size)

    def poke(self, address: int, data: bytes):
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_POKE,
            'data': {'address': address, 'size': len(data), 'data': data},
        })
        self._sock.sendall(message)

    def peek_str(self, address: int) -> str:
        s = self.symbol(address)
        return s.peek(self.symbols.strlen(s))

    def put_file(self, filename: str, buf: bytes):
        fd = self.open(filename, os.O_WRONLY | os.O_CREAT)
        assert fd >= 0

        while buf:
            err = self.write(fd, buf)
            if err < 0:
                raise IOError()
            buf = buf[err:]

        self.close(fd)
        return buf

    def get_file(self, filename: str) -> bytes:
        fd = self.open(filename, os.O_RDONLY)
        assert fd >= 0
        buf = b''
        while True:
            err, chunk = self.read(fd)
            buf += chunk
            if err == 0:
                break
            elif err < 0:
                raise IOError()
        self.close(fd)
        return buf

    def shell(self, argv: typing.List[str] = None):
        if argv is None:
            argv = self.DEFAULT_ARGV

        pid = self._execute(argv)
        logging.info(f'shell process started as pid: {pid}')

        self._sock.setblocking(False)

        self._prepare_terminal()
        try:
            result = self._execution_loop()
        except Exception:
            self._restore_terminal()
            self._reconnect()
            raise

        self._restore_terminal()
        self._reconnect()

        return result

    def objc_call(self, objc_object: int, selector, *params):
        return self.symbols.objc_msgSend(objc_object, self.symbols.sel_getUid(selector), *params)

    def symbol(self, symbol: int):
        return Symbol.create(symbol, self)

    @staticmethod
    def _add_global(name, value, reserved_names=None):
        if reserved_names is None or name not in reserved_names:
            # don't override existing symbols
            globals()[name] = value

    def _globalize_commands(self):
        """ Make all command available in global scope. """
        reserved_names = list(globals().keys()) + dir(builtins)

        for command_name, function in self.commands:
            command_func = partial(function, self)
            command_func.__doc__ = function.__doc__

            self._add_global(command_name, command_func, reserved_names)

    def _ipython_run_cell_hook(self, info):
        """
        Enable lazy loading for symbols
        :param info: IPython's CellInfo object
        """
        for node in ast.walk(ast.parse(info.raw_cell)):
            if not isinstance(node, ast.Name):
                # we are only interested in names
                continue

            if node.id in locals() or node.id in globals() or node.id in dir(builtins):
                # That are undefined
                continue

            if not hasattr(SymbolsJar, node.id):
                # ignore SymbolsJar properties
                try:
                    symbol = getattr(self.symbols, node.id)
                except SymbolAbsentError:
                    pass
                else:
                    self._add_global(
                        node.id,
                        symbol
                    )

    def interactive(self):
        """ Start an interactive shell """
        self._globalize_commands()

        sys.argv = ['a']
        c = Config()
        c.IPCompleter.use_jedi = False
        c.InteractiveShellApp.exec_lines = [
            '''IPython.get_ipython().events.register('pre_run_cell', self._ipython_run_cell_hook)'''
        ]
        namespace = globals()
        namespace.update(locals())

        IPython.start_ipython(config=c, user_ns=namespace)

    def _reconnect(self):
        self._sock = socket()
        self._sock.connect((self._hostname, self._port))

    def _execute(self, argv: typing.List[str]) -> int:
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_EXEC,
            'data': {'argv': argv},
        })
        self._sock.sendall(message)
        pid = pid_t.parse(self._sock.recv(pid_t.sizeof()))
        return pid

    def _restore_terminal(self):
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, self._old_settings)

    def _prepare_terminal(self):
        fd = sys.stdin.fileno()
        self._old_settings = termios.tcgetattr(fd)

        atexit.register(self._restore_terminal)

        new = termios.tcgetattr(fd)
        new[3] &= ~(termios.ECHO | termios.ICANON)
        new[6][termios.VMIN] = 1
        new[6][termios.VTIME] = 0

        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, new)

    def _recvall(self, size: int) -> bytes:
        buf = b''
        while size:
            try:
                chunk = self._sock.recv(size)
            except BlockingIOError:
                continue
            size -= len(chunk)
            buf += chunk
        return buf

    def _execution_loop(self):
        while True:
            rlist, _, _ = select([sys.stdin, self._sock], [], [])

            for fd in rlist:
                if fd == sys.stdin:
                    buf = os.read(sys.stdin.fileno(), CHUNK_SIZE)
                    self._sock.sendall(buf)
                elif fd == self._sock:
                    try:
                        buf = self._recvall(exec_chunk_t.sizeof())
                    except ConnectionResetError:
                        print('Bye. 👋')
                        return

                    exec_chunk = exec_chunk_t.parse(buf)
                    data = self._recvall(exec_chunk.size)

                    if exec_chunk.chunk_type == exec_chunk_type_t.CMD_EXEC_CHUNK_TYPE_STDOUT:
                        sys.stdout.write(data.decode())
                        sys.stdout.flush()
                    elif exec_chunk.chunk_type == exec_chunk_type_t.CMD_EXEC_CHUNK_TYPE_ERRORCODE:
                        return exitcode_t.parse(data)
