import ast
import atexit
import builtins
import contextlib
import logging
import os
import sys
import termios
import typing
from select import select
from socket import socket

import IPython
from cached_property import cached_property
from construct import Int64sl
from traitlets.config import Config

from pyzshell.exceptions import ArgumentError, SymbolAbsentError
from pyzshell.fs import Fs
from pyzshell.processes import Processes
from pyzshell.protocol import protocol_message_t, cmd_type_t, pid_t, exec_chunk_t, exec_chunk_type_t, exitcode_t
from pyzshell.structs.linux import utsname as utsname_linux
from pyzshell.structs.darwin import utsname as utsname_darwin
from pyzshell.symbol import Symbol, DrawinSymbol
from pyzshell.symbols_jar import SymbolsJar

DEFAULT_PORT = 5910
CHUNK_SIZE = 1024

USAGE = '''
Welcome to iShell! You interactive shell for controlling the remote zShell server.
Feel free to use the following globals:

🌍 p - the injected process
🌍 symbols - process global symbols

Have a nice flight ✈️!
Starting an IPython shell... 🐍
'''


class Client:
    DEFAULT_ARGV = ['/bin/sh']

    def __init__(self, hostname: str, port: int = None):
        self._hostname = hostname
        self._port = port
        self._sock = None
        self._old_settings = None
        self._reconnect()
        self._endianness = '<'
        self.symbols = SymbolsJar.create(self)
        self.fs = Fs(self)
        self.processes = Processes(self)

    def info(self):
        """ print information about current target """
        uname = self.uname
        print('sysname:', uname.sysname)
        print('nodename:', uname.nodename)
        print('release:', uname.release)
        print('version:', uname.version)
        print('machine:', uname.machine)
        print(f'uid: {self.symbols.getuid():d}')
        print(f'gid: {self.symbols.getgid():d}')
        print(f'pid: {self.symbols.getpid():d}')
        print(f'ppid: {self.symbols.getppid():d}')
        print(f'progname: {self.symbols.getprogname().peek_str()}')

    def iter_libraries(self):
        for i in range(self.symbols._dyld_image_count()):
            yield self.symbols._dyld_get_image_name(i).peek_str()

    def dlopen(self, filename: str, mode: int) -> Symbol:
        """ call dlopen() at remote and return its handle. see the man page for more details. """
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_DLOPEN,
            'data': {'filename': filename, 'mode': mode},
        })
        self._sock.sendall(message)
        err = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        return self.symbol(err)

    def dlclose(self, lib: int):
        """ call dlclose() at remote and return its handle. see the man page for more details. """
        lib &= 0xffffffffffffffff
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_DLCLOSE,
            'data': {'lib': lib},
        })
        self._sock.sendall(message)
        err = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        return err

    def dlsym(self, lib: int, symbol_name: str):
        """ call dlsym() at remote and return its handle. see the man page for more details. """
        lib &= 0xffffffffffffffff
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_DLSYM,
            'data': {'lib': lib, 'symbol_name': symbol_name},
        })
        self._sock.sendall(message)
        err = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        return err

    def call(self, address: int, argv: typing.List[int] = None) -> Symbol:
        """ call a remote function and retrieve its return value as Symbol object """
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
        """ peek data at given address """
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_PEEK,
            'data': {'address': address, 'size': size},
        })
        self._sock.sendall(message)
        return self._recvall(size)

    def poke(self, address: int, data: bytes):
        """ poke data at given address """
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_POKE,
            'data': {'address': address, 'size': len(data), 'data': data},
        })
        self._sock.sendall(message)

    def spawn(self, argv: typing.List[str] = None):
        """ spawn a new process and forward its stdin, stdout & stderr """
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

    def symbol(self, symbol: int):
        """ at a symbol object from a given address """
        return DrawinSymbol.create(symbol, self)

    @contextlib.contextmanager
    def safe_malloc(self, size: int):
        x = self.symbols.malloc(size)
        try:
            yield x
        finally:
            self.symbols.free(x)

    @cached_property
    def os_family(self):
        with self.safe_malloc(1024 * 20) as block:
            assert 0 == self.symbols.uname(block)
            return block.peek_str().lower()

    @cached_property
    def uname(self):
        # by default, assume linux
        utsname = utsname_linux
        if self.os_family == 'darwin':
            utsname = utsname_darwin
        with self.safe_malloc(utsname.sizeof()) as uname:
            assert 0 == self.symbols.uname(uname)
            return utsname.parse(uname.peek(utsname.sizeof()))

    def interactive(self):
        """ Start an interactive shell """
        sys.argv = ['a']
        c = Config()
        c.IPCompleter.use_jedi = False
        c.InteractiveShellApp.exec_lines = [
            '''IPython.get_ipython().events.register('pre_run_cell', p._ipython_run_cell_hook)'''
        ]
        namespace = globals()
        namespace.update({'p': self, 'symbols': self.symbols})
        print(USAGE)
        IPython.start_ipython(config=c, user_ns=namespace)

    def _add_global(self, name, value):
        globals()[name] = value

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

    def __repr__(self):
        buf = '<'
        buf += f'PID:{self.symbols.getpid():d} UID:{self.symbols.getuid():d} GID:{self.symbols.getgid():d} ' \
               f'VERSION:{self.uname.version}'
        buf += '>'
        return buf
