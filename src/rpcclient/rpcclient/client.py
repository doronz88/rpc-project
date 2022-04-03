import ast
import builtins
import contextlib
import logging
import os
import sys
import typing
from collections import namedtuple
from enum import Enum
from select import select
from socket import socket

import IPython
from construct import Float64l, Float32l, Float16l
from traitlets.config import Config

from rpcclient.client_connection import ClientConnection
from rpcclient.darwin.structs import exitcode_t
from rpcclient.exceptions import ArgumentError, SymbolAbsentError, ServerDiedError, \
    InvalidServerVersionMagicError
from rpcclient.fs import Fs
from rpcclient.lief import Lief
from rpcclient.network import Network
from rpcclient.processes import Processes
from rpcclient.protocol import protocol_message_t, cmd_type_t, exec_chunk_t, exec_chunk_type_t, \
    SERVER_MAGIC_VERSION, argument_type_t, arch_t, \
    protocol_handshake_t
from rpcclient.rpc_commands import RPCDlopenCommand, RPCDlsymCommand, RPCDlcloseCommand, RPCPeekCommand, RPCPokeCommand, \
    RPCGetDummyBlockCommand, RPCExecuteCommand, RPCCallCommand
from rpcclient.symbol import Symbol
from rpcclient.symbols_jar import SymbolsJar
from rpcclient.sysctl import Sysctl

tty_support = False
try:
    import termios
    import tty

    tty_support = True
except ImportError:
    logging.warning('termios not available on your system. some functionality may not work as expected')

io_or_str = typing.TypeVar('io_or_str', typing.IO, str)

SpawnResult = namedtuple('SpawnResult', 'error pid stdout')

CHUNK_SIZE = 1024

USAGE = '''
Welcome to the rpcclient interactive shell! You interactive shell for controlling the remote rpcserver.
Feel free to use the following globals:

🌍 p - the injected process
🌍 symbols - process global symbols

Have a nice flight ✈️!
Starting an IPython shell... 🐍
'''


class Client:
    """ Main client interface to access remote rpcserver """

    DEFAULT_ARGV = ['/bin/sh']
    DEFAULT_ENVP = []

    def __init__(self, sock, sysname: str, arch: arch_t, hostname: str, port: int = None):
        self._arch = arch
        self._hostname = hostname
        self._port = port
        self._sock = sock
        self._client_connection = ClientConnection(sock)
        self._old_settings = None
        self._endianness = '<'
        self._sysname = sysname
        self._dlsym_global_handle = -1  # RTLD_NEXT

        # whether the system uses inode structs of 64 bits
        self.inode64 = False

        self.symbols = SymbolsJar.create(self)
        self.fs = Fs(self)
        self.processes = Processes(self)
        self.network = Network(self)
        self.lief = Lief(self)
        self.sysctl = Sysctl(self)

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

    @property
    def uname(self):
        """ get the utsname struct from remote """
        raise NotImplementedError()

    @property
    def arch(self):
        """ get remote arch """
        return self._arch

    def dlopen(self, filename: str, mode: int) -> Symbol:
        """ call dlopen() at remote and return its handle. see the man page for more details. """
        return self.symbol(self._client_connection.send_command(RPCDlopenCommand(filename, mode)))

    def dlclose(self, lib: int):
        """ call dlclose() at remote and return its handle. see the man page for more details. """
        lib &= 0xffffffffffffffff
        return self._client_connection.send_command(RPCDlcloseCommand(lib))

    def dlsym(self, lib: int, symbol_name: str):
        """ call dlsym() at remote and return its handle. see the man page for more details. """
        lib &= 0xffffffffffffffff
        return self._client_connection.send_command(RPCDlsymCommand(lib, symbol_name))

    def call(self, address: int, argv: typing.List[int] = None, return_float64=False, return_float32=False,
             return_float16=False, return_raw=False) -> Symbol:
        """ call a remote function and retrieve its return value as Symbol object """
        fixed_argv = []
        free_list = []

        for arg in argv:
            if isinstance(arg, Enum):
                # if it's a python enum, then first get its real value and only then attempt to convert
                arg = arg.value

            tmp = arg

            if isinstance(arg, bool):
                tmp = int(arg)

            elif isinstance(arg, str):
                tmp = self.symbols.malloc(len(arg) + 1)
                tmp.poke(arg.encode() + b'\0')
                free_list.append(tmp)

            elif isinstance(arg, bytes):
                tmp = self.symbols.malloc(len(arg))
                tmp.poke(arg)
                free_list.append(tmp)

            if isinstance(tmp, int):
                tmp &= 0xffffffffffffffff
                fixed_argv.append({'type': argument_type_t.Integer, 'value': tmp})

            elif isinstance(tmp, float):
                fixed_argv.append({'type': argument_type_t.Double, 'value': tmp})

            else:
                raise ArgumentError(f'invalid parameter type: {arg}')

        response = self._client_connection.send_command(RPCCallCommand(address, fixed_argv))

        for f in free_list:
            self.symbols.free(f)

        if self.arch == arch_t.ARCH_ARM64:
            double_buf = Float64l.build(response.return_values.arm_registers.d[0])
            float16_err = Float16l.parse(double_buf)
            float32_err = Float32l.parse(double_buf)
            float64_err = response.return_values.arm_registers.d[0]

            if return_float16:
                return float16_err

            if return_float32:
                return float32_err

            if return_float64:
                return float64_err

            if return_raw:
                return response.return_values.arm_registers

            return self.symbol(response.return_values.arm_registers.x[0])

        return self.symbol(response.return_values.return_value)

    def peek(self, address: int, size: int) -> bytes:
        """ peek data at given address """
        return self._client_connection.send_command(RPCPeekCommand(address, size))

    def poke(self, address: int, data: bytes):
        """ poke data at given address """
        self._client_connection.send_command(RPCPokeCommand(address, data))

    def get_dummy_block(self) -> Symbol:
        """ get an address for a stub block containing nothing """
        return self.symbol(self._client_connection.send_command(RPCGetDummyBlockCommand()))

    def spawn(self, argv: typing.List[str] = None, envp: typing.List[str] = None, stdin: io_or_str = sys.stdin,
              stdout=sys.stdout, raw_tty=False, background=False) -> SpawnResult:
        """
        spawn a new process and forward its stdin, stdout & stderr

        :param argv: argv of the process to be executed
        :param envp: envp of the process to be executed
        :param stdin: either a file object to read from OR a string
        :param stdout: a file object to write both stdout and stderr to. None if background is requested
        :param raw_tty: should enable raw tty mode
        :param background: should execute process in background
        :return: a SpawnResult. error is None if background is requested
        """
        if argv is None:
            argv = self.DEFAULT_ARGV

        if envp is None:
            envp = self.DEFAULT_ENVP

        def execution_loop_function(server_socket, read_function, write_function):
            fds = []
            if hasattr(stdin, 'fileno'):
                fds.append(stdin)
            else:
                # assume it's just raw bytes
                write_function(stdin.encode())
            fds.append(server_socket)

            while True:
                rlist, _, _ = select(fds, [], [])

                for fd in rlist:
                    if fd == sys.stdin:
                        if stdin == sys.stdin:
                            buf = os.read(stdin.fileno(), CHUNK_SIZE)
                        else:
                            buf = stdin.read(CHUNK_SIZE)
                        write_function(buf)
                    elif fd == server_socket:
                        try:
                            data, err = read_function()
                        except ConnectionResetError:
                            print('Bye. 👋')
                            return

                        if data is not None:
                            stdout.write(data)
                            stdout.flush()

                        if err is not None:
                            return err

        pre_func = None
        post_func = None

        if raw_tty:
            pre_func = self._prepare_terminal
            post_func = self._restore_terminal

        pid, error = self._client_connection.send_command(
            RPCExecuteCommand(argv, envp, background, execution_loop_function, pre_func, post_func))

        return SpawnResult(error=error, pid=pid, stdout=stdout)

    def symbol(self, symbol: int):
        """ at a symbol object from a given address """
        return Symbol.create(symbol, self)

    @property
    def errno(self):
        return self.symbols.errno[0]

    @errno.setter
    def errno(self, value):
        self.symbols.errno[0] = value

    @property
    def last_error(self):
        """ get info about the last occurred error """
        if not self.errno:
            return ''
        err_str = self.symbols.strerror(self.errno).peek_str()
        return f'[{self.errno}] {err_str}'

    @property
    def environ(self) -> typing.List[str]:
        result = []
        environ = self.symbols.environ[0]
        i = 0
        while environ[i]:
            result.append(environ[i].peek_str())
            i += 1
        return result

    def setenv(self, name: str, value: str):
        """ set process environment variable """
        self.symbols.setenv(name, value)

    def getenv(self, name: str) -> typing.Optional[str]:
        """ get process environment variable """
        value = self.symbols.getenv(name)
        if not value:
            return None
        return value.peek_str()

    @property
    def pid(self):
        return int(self.symbols.getpid())

    @contextlib.contextmanager
    def safe_calloc(self, size: int):
        with self.safe_malloc(size) as x:
            x.poke(b'\x00' * size)
            try:
                yield x
            finally:
                pass

    @contextlib.contextmanager
    def safe_malloc(self, size: int):
        with self.freeing(self.symbols.malloc(size)) as x:
            yield x

    @contextlib.contextmanager
    def freeing(self, symbol):
        try:
            yield symbol
        finally:
            if symbol:
                self.symbols.free(symbol)

    def interactive(self):
        """ Start an interactive shell """
        sys.argv = ['a']
        c = Config()
        c.IPCompleter.use_jedi = False
        c.InteractiveShellApp.exec_lines = [
            '''IPython.get_ipython().events.register('pre_run_cell', p._ipython_run_cell_hook)'''
        ]
        c.TerminalInteractiveShell.autoformatter = None
        namespace = globals()
        namespace.update({'p': self, 'symbols': self.symbols})
        print(USAGE)
        IPython.start_ipython(config=c, user_ns=namespace)

    def _add_global(self, name, value):
        globals()[name] = value

    def _ipython_run_cell_hook(self, info):
        """
        Enable lazy loading for symbols
        :param info: IPython's CellInf4o object
        """
        if info.raw_cell.startswith('!') or info.raw_cell.endswith('?'):
            return

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

    def close(self):
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_CLOSE,
            'data': None,
        })
        self._sock.sendall(message)
        self._sock.close()

    def reconnect(self):
        """ close current socket and attempt to reconnect """
        self.close()
        self._sock = socket()
        self._sock.connect((self._hostname, self._port))

        handshake = protocol_handshake_t.parse(self._recvall(protocol_handshake_t.sizeof()))

        if handshake.magic != SERVER_MAGIC_VERSION:
            raise InvalidServerVersionMagicError()

    def _restore_terminal(self):
        if not tty_support:
            return
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_settings)

    def _prepare_terminal(self):
        if not tty_support:
            return
        fd = sys.stdin
        self._old_settings = termios.tcgetattr(fd)
        tty.setraw(fd)

    def _recvall(self, size: int) -> bytes:
        buf = b''
        while size:
            try:
                chunk = self._sock.recv(size)
            except BlockingIOError:
                continue
            if self._sock.gettimeout() == 0 and not chunk:
                # TODO: replace self._sock.gettimeout() == 0 on -> self._sock.getblocking() on python37+
                raise ServerDiedError()
            size -= len(chunk)
            buf += chunk
        return buf

    def _execution_loop(self, stdin: io_or_str = sys.stdin, stdout=sys.stdout):
        """
        if stdin is a file object, we need to select between the fds and give higher priority to stdin.
        otherwise, we can simply write all stdin contents directly to the process
        """
        fds = []
        if hasattr(stdin, 'fileno'):
            fds.append(stdin)
        else:
            # assume it's just raw bytes
            self._sock.sendall(stdin.encode())
        fds.append(self._sock)

        while True:
            rlist, _, _ = select(fds, [], [])

            for fd in rlist:
                if fd == sys.stdin:
                    if stdin == sys.stdin:
                        buf = os.read(stdin.fileno(), CHUNK_SIZE)
                    else:
                        buf = stdin.read(CHUNK_SIZE)
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
                        stdout.write(data.decode())
                        stdout.flush()
                    elif exec_chunk.chunk_type == exec_chunk_type_t.CMD_EXEC_CHUNK_TYPE_ERRORCODE:
                        return exitcode_t.parse(data)

    def __repr__(self):
        buf = f'<{self.__class__.__name__} '
        buf += f'PID:{self.symbols.getpid():d} UID:{self.symbols.getuid():d} GID:{self.symbols.getgid():d} ' \
               f'SYSNAME:{self._sysname} ARCH:{self.arch}'
        buf += '>'
        return buf
