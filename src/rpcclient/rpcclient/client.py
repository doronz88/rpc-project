import ast
import builtins
import contextlib
import dataclasses
import logging
import os
import sys
import threading
import typing
from collections import namedtuple
from enum import Enum
from pathlib import Path
from select import select

import IPython
from construct import Float16l, Float32l, Float64l, Int64sl, Int64ul
from traitlets.config import Config
from xonsh.built_ins import XSH
from xonsh.main import main as xonsh_main

import rpcclient
from rpcclient.darwin.structs import exitcode_t, pid_t
from rpcclient.exceptions import ArgumentError, BadReturnValueError, InvalidServerVersionMagicError, \
    RpcBrokenPipeError, RpcConnectionRefusedError, RpcFileExistsError, RpcFileNotFoundError, RpcIsADirectoryError, \
    RpcNotADirectoryError, RpcNotEmptyError, RpcPermissionError, RpcResourceTemporarilyUnavailableError, \
    ServerDiedError, SpawnError, SymbolAbsentError
from rpcclient.fs import Fs
from rpcclient.lief import Lief
from rpcclient.network import Network
from rpcclient.processes import Processes
from rpcclient.protocol import MAGIC, SERVER_MAGIC_VERSION, arch_t, argument_type_t, call_response_t, \
    call_response_t_size, cmd_type_t, dummy_block_t, exec_chunk_t, exec_chunk_type_t, listdir_entry_t, \
    protocol_handshake_t, protocol_message_t, reply_protocol_message_t
from rpcclient.structs.consts import EAGAIN, ECONNREFUSED, EEXIST, EISDIR, ENOENT, ENOTDIR, ENOTEMPTY, EPERM, EPIPE
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


@dataclasses.dataclass
class ProtocolDitentStat:
    errno: int
    st_dev: int  # device inode resides on
    st_mode: int  # inode protection mode
    st_nlink: int  # number of hard links to the file
    st_ino: int  # inode's number
    st_uid: int  # user-id of owner
    st_gid: int  # group-id of owner
    st_rdev: int  # device type, for special file inode
    st_size: int  # file size, in bytes
    st_blocks: int  # blocks allocated for file
    st_blksize: int  # optimal blocksize for I/O
    st_atime: int
    st_mtime: int
    st_ctime: int


@dataclasses.dataclass
class ProtocolDirent:
    d_inode: int
    d_type: int
    d_name: str
    lstat: ProtocolDitentStat
    stat: ProtocolDitentStat


class Client:
    """ Main client interface to access remote rpcserver """

    DEFAULT_ARGV = ['/bin/sh']
    DEFAULT_ENVP = []

    def __init__(self, sock, sysname: str, arch: arch_t, create_socket_cb: typing.Callable):
        self._arch = arch
        self._create_socket_cb = create_socket_cb
        self._sock = sock
        self._old_settings = None
        self._endianness = '<'
        self._sysname = sysname
        self._dlsym_global_handle = -1  # RTLD_NEXT
        self._protocol_lock = threading.Lock()
        self._logger = logging.getLogger(self.__module__)
        self._ipython_run_cell_hook_enabled = True

        self.reconnect_lock = threading.Lock()

        self._init_process_specific()

    def _init_process_specific(self):
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
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_DLOPEN,
            'data': {'filename': filename, 'mode': mode},
        })
        with self._protocol_lock:
            self._sock.sendall(message)
            address = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        return self.symbol(address)

    def dlclose(self, lib: int):
        """ call dlclose() at remote and return its handle. see the man page for more details. """
        lib &= 0xffffffffffffffff
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_DLCLOSE,
            'data': {'lib': lib},
        })
        with self._protocol_lock:
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
        with self._protocol_lock:
            self._sock.sendall(message)
            address = Int64sl.parse(self._recvall(Int64sl.sizeof()))
        return address

    def call(self, address: int, argv: typing.List[int] = None, return_float64=False, return_float32=False,
             return_float16=False, return_raw=False, va_list_index: int = 0xffff) -> Symbol:
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
                [self.symbols.free(f) for f in free_list]
                raise ArgumentError(f'invalid parameter type: {arg}')

        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_CALL,
            'data': {'address': address, 'va_list_index': va_list_index, 'argv': fixed_argv},
        })

        with self._protocol_lock:
            self._sock.sendall(message)
            response = call_response_t.parse(self._recvall(call_response_t_size))

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
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_PEEK,
            'data': {'address': address, 'size': size},
        })
        with self._protocol_lock:
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
        with self._protocol_lock:
            self._sock.sendall(message)
            reply = protocol_message_t.parse(self._recvall(reply_protocol_message_t.sizeof()))
            if reply.cmd_type == cmd_type_t.CMD_REPLY_ERROR:
                raise ArgumentError(f'failed to write {len(data)} bytes to {address}')

    def get_dummy_block(self) -> Symbol:
        """ get an address for a stub block containing nothing """
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_GET_DUMMY_BLOCK,
            'data': None,
        })

        with self._protocol_lock:
            self._sock.sendall(message)
            result = dummy_block_t.parse(self._recvall(dummy_block_t.sizeof()))

        return self.symbol(result)

    def listdir(self, filename: str):
        """ get an address for a stub block containing nothing """
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_LISTDIR,
            'data': {'filename': filename},
        })

        entries = []
        with self._protocol_lock:
            self._sock.sendall(message)
            dirp = Int64ul.parse(self._recvall(Int64ul.sizeof()))
            while dirp:
                magic = Int64ul.parse(self._recvall(Int64ul.sizeof()))
                if magic != MAGIC:
                    break
                entry = listdir_entry_t.parse(self._recvall(listdir_entry_t.sizeof()))
                name = self._recvall(entry.d_namlen).decode()
                lstat = ProtocolDitentStat(
                    errno=entry.lstat.errno, st_blocks=entry.lstat.st_blocks, st_blksize=entry.lstat.st_blksize,
                    st_atime=entry.lstat.st_atime, st_ctime=entry.lstat.st_ctime, st_mtime=entry.lstat.st_mtime,
                    st_nlink=entry.lstat.st_nlink, st_mode=entry.lstat.st_mode, st_rdev=entry.lstat.st_rdev,
                    st_size=entry.lstat.st_size, st_dev=entry.lstat.st_dev, st_gid=entry.lstat.st_gid,
                    st_ino=entry.lstat.st_ino, st_uid=entry.lstat.st_uid)
                stat = ProtocolDitentStat(
                    errno=entry.stat.errno, st_blocks=entry.stat.st_blocks, st_blksize=entry.stat.st_blksize,
                    st_atime=entry.stat.st_atime, st_ctime=entry.stat.st_ctime, st_mtime=entry.stat.st_mtime,
                    st_nlink=entry.stat.st_nlink, st_mode=entry.stat.st_mode, st_rdev=entry.stat.st_rdev,
                    st_size=entry.stat.st_size, st_dev=entry.stat.st_dev, st_gid=entry.stat.st_gid,
                    st_ino=entry.stat.st_ino, st_uid=entry.stat.st_uid)
                entries.append(ProtocolDirent(d_inode=entry.lstat.st_ino, d_type=entry.d_type, d_name=name, lstat=lstat,
                                              stat=stat))

        if not dirp:
            self.raise_errno_exception(f'failed to listdir: {filename}')

        return entries

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

        with self._protocol_lock:
            try:
                pid = self._execute(argv, envp, background=background)
            except SpawnError:
                # depends on where the error occurred, the socket might be closed
                raise

            self._logger.info(f'shell process started as pid: {pid}')

            if background:
                return SpawnResult(error=None, pid=pid, stdout=None)

            if raw_tty:
                self._prepare_terminal()
            try:
                # the socket must be non-blocking for using select()
                self._sock.setblocking(False)
                error = self._execution_loop(stdin, stdout)
            except Exception:  # noqa: E722
                # this is important to really catch every exception here, even exceptions not inheriting from Exception
                # so the controlling terminal will remain working with its previous settings
                if raw_tty:
                    self._restore_terminal()
                raise
            finally:
                self._sock.setblocking(True)

        if raw_tty:
            self._restore_terminal()

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

    def interactive(self, additional_namespace: typing.Mapping = None):
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
        if additional_namespace is not None:
            namespace.update(additional_namespace)
        print(USAGE)
        IPython.start_ipython(config=c, user_ns=namespace)

    def _add_global(self, name: str, value) -> None:
        globals()[name] = value

    def _ipython_run_cell_hook(self, info):
        """
        Enable lazy loading for symbols
        :param info: IPython's CellInf4o object
        """
        if not self._ipython_run_cell_hook_enabled:
            return

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

    def _close(self):
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_CLOSE,
            'data': None,
        })
        self._sock.sendall(message)
        self._sock.close()

    def close(self):
        with self._protocol_lock:
            self._close()

    def shell(self):
        self._logger.disabled = True
        self._ipython_run_cell_hook_enabled = False

        args = ['--rc']
        home_rc = Path('~/.xonshrc').expanduser()
        if home_rc.exists():
            args.append(str(home_rc.expanduser().absolute()))
        args.append(str((Path(rpcclient.__file__).parent / 'xonshrc.py').absolute()))
        XSH.ctx['_create_socket_cb'] = self._create_socket_cb

        try:
            logging.getLogger('parso.python.diff').disabled = True
            logging.getLogger('parso.cache').disabled = True
            xonsh_main(args)
        except SystemExit:
            self._logger.disabled = False
            self._ipython_run_cell_hook_enabled = True

    def reconnect(self):
        """ close current socket and attempt to reconnect """
        with self.reconnect_lock:
            with self._protocol_lock:
                self._close()
                self._sock = self._create_socket_cb()
                handshake = protocol_handshake_t.parse(self._recvall(protocol_handshake_t.sizeof()))

            if handshake.magic != SERVER_MAGIC_VERSION:
                raise InvalidServerVersionMagicError()

            # new clients are handled in new processes so all symbols may reside in different addresses
            self._init_process_specific()

    def _execute(self, argv: typing.List[str], envp: typing.List[str], background=False) -> int:
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_EXEC,
            'data': {'background': background, 'argv': argv, 'envp': envp},
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
                        # WEXITSTATUS(x)
                        return exitcode_t.parse(data) >> 8

    def raise_errno_exception(self, message: str):
        message += f' ({self.last_error})'
        exceptions = {
            EPERM: RpcPermissionError,
            ENOENT: RpcFileNotFoundError,
            EEXIST: RpcFileExistsError,
            EISDIR: RpcIsADirectoryError,
            ENOTDIR: RpcNotADirectoryError,
            EPIPE: RpcBrokenPipeError,
            ENOTEMPTY: RpcNotEmptyError,
            EAGAIN: RpcResourceTemporarilyUnavailableError,
            ECONNREFUSED: RpcConnectionRefusedError,
        }
        exception = exceptions.get(self.errno)
        if exception:
            raise exception(message)
        raise BadReturnValueError(message)

    def __repr__(self):
        buf = f'<{self.__class__.__name__} '
        buf += f'PID:{self.symbols.getpid():d} UID:{self.symbols.getuid():d} GID:{self.symbols.getgid():d} ' \
               f'SYSNAME:{self._sysname} ARCH:{self.arch}'
        buf += '>'
        return buf
