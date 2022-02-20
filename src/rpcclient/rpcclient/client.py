import ast
import atexit
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
from construct import Int64sl
from traitlets.config import Config

from rpcclient.darwin.structs import pid_t, exitcode_t
from rpcclient.exceptions import ArgumentError, SymbolAbsentError, SpawnError, ServerDiedError, \
    InvalidServerVersionMagicError
from rpcclient.fs import Fs
from rpcclient.network import Network
from rpcclient.processes import Processes
from rpcclient.protocol import protocol_message_t, cmd_type_t, exec_chunk_t, exec_chunk_type_t, UNAME_VERSION_LEN, \
    reply_protocol_message_t, dummy_block_t, SERVER_MAGIC_VERSION
from rpcclient.symbol import Symbol
from rpcclient.symbols_jar import SymbolsJar

tty_support = False
try:
    import termios
    import tty

    tty_support = True
except ImportError:
    logging.warning('termios not available on your system. some functionality may not work as expected')

SpawnResult = namedtuple('SpawnResult', 'error pid stdout')

INVALID_PID = 0xffffffff
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

    def __init__(self, sock, sysname: str, hostname: str, port: int = None):
        self._hostname = hostname
        self._port = port
        self._sock = sock
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

    def uname(self):
        """ get the utsname struct from remote """
        raise NotImplementedError()

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
        reply = protocol_message_t.parse(self._recvall(reply_protocol_message_t.sizeof()))
        if reply.cmd_type == cmd_type_t.CMD_REPLY_ERROR:
            raise ArgumentError(f'failed to read {size} bytes from {address}')
        return self._recvall(size)

    def poke(self, address: int, data: bytes):
        """ poke data at given address """
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_POKE,
            'data': {'address': address, 'size': len(data), 'data': data},
        })
        self._sock.sendall(message)

    def get_dummy_block(self) -> Symbol:
        """ get an address for a stub block containing nothing """
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_GET_DUMMY_BLOCK,
            'data': None,
        })
        self._sock.sendall(message)
        return self.symbol(dummy_block_t.parse(self._recvall(8)))

    def spawn(self, argv: typing.List[str] = None, envp: typing.List[str] = None, stdin=sys.stdin, stdout=sys.stdout,
              tty=False, background=False) -> SpawnResult:
        """
        spawn a new process and forward its stdin, stdout & stderr

        :param argv: argv of the process to be executed
        :param envp: envp of the process to be executed
        :param stdin: either a file object to read from or a string
        :param stdout: a file object to write both stdout and stderr to
        :param tty: should enable raw tty mode
        :param background: should execute process in background
        :return: a SpawnResult. error is None if background is requested
        """
        if argv is None:
            argv = self.DEFAULT_ARGV

        if envp is None:
            envp = self.DEFAULT_ENVP

        try:
            pid = self._execute(argv, envp)
        except SpawnError:
            # depends on where the error occurred, the socket might be closed
            self.reconnect()
            raise

        logging.info(f'shell process started as pid: {pid}')

        if background:
            # if in background was requested, we can just detach this connection
            self.reconnect()
            return SpawnResult(error=None, pid=pid, stdout=stdout)

        self._sock.setblocking(False)

        if tty:
            self._prepare_terminal()
        try:
            error = self._execution_loop(stdin, stdout)
        except Exception:  # noqa: E722
            # this is important to really catch every exception here, even exceptions not inheriting from Exception
            # so the controlling terminal will remain working with its previous settings
            if tty:
                self._restore_terminal()
            self.reconnect()
            raise

        if tty:
            self._restore_terminal()
        self.reconnect()

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

    def reconnect(self):
        """ close current socket and attempt to reconnect """
        self._sock = socket()
        self._sock.connect((self._hostname, self._port))
        magic = self._recvall(len(SERVER_MAGIC_VERSION))

        if magic != SERVER_MAGIC_VERSION:
            raise InvalidServerVersionMagicError(f'got an invalid server magic: {magic.hex()}')

        self._recvall(UNAME_VERSION_LEN)

    def _execute(self, argv: typing.List[str], envp: typing.List[str]) -> int:
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_EXEC,
            'data': {'argv': argv, 'envp': envp},
        })
        self._sock.sendall(message)
        pid = pid_t.parse(self._sock.recv(pid_t.sizeof()))
        if pid == INVALID_PID:
            raise SpawnError(f'failed to spawn: {argv}')
        return pid

    def _restore_terminal(self):
        if not tty_support:
            return
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_settings)

    def _prepare_terminal(self):
        if not tty_support:
            return
        fd = sys.stdin
        self._old_settings = termios.tcgetattr(fd)
        atexit.register(self._restore_terminal)
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

    def _execution_loop(self, stdin=sys.stdin, stdout=sys.stdout):
        """
        if stdin is a file object, we need to select between the fds and give higher priority to stdin.
        otherwise, we can simply write all stdin contents directly to the process
        """
        fds = []
        if hasattr(stdin, 'fileno'):
            fds.append(stdin)
        else:
            # assume it's just raw bytes
            self._sock.sendall(stdin)
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
               f'SYSNAME:{self._sysname}'
        buf += '>'
        return buf
