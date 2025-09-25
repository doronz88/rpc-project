import contextlib
import ctypes
import dataclasses
import logging
import os
import sys
import threading
import typing
from collections import namedtuple
from enum import Enum, auto
from functools import wraps
from pathlib import Path
from select import select
from typing import Any, Optional

from cached_property import cached_property
from xonsh.built_ins import XSH
from xonsh.main import main as xonsh_main

from rpcclient.core.capture_fd import CaptureFD
from rpcclient.core.structs.consts import EAGAIN, ECONNREFUSED, EEXIST, EISDIR, ENOENT, ENOTDIR, ENOTEMPTY, EPERM, \
    EPIPE, RTLD_NEXT
from rpcclient.core.subsystems.decorator import subsystem
from rpcclient.core.subsystems.fs import Fs
from rpcclient.core.subsystems.lief import Lief
from rpcclient.core.subsystems.network import Network
from rpcclient.core.subsystems.processes import Processes
from rpcclient.core.subsystems.sysctl import Sysctl
from rpcclient.core.symbol import Symbol
from rpcclient.core.symbols_jar import SymbolsJar
from rpcclient.event_notifier import EventNotifier
from rpcclient.exceptions import ArgumentError, BadReturnValueError, RpcBrokenPipeError, RpcConnectionRefusedError, \
    RpcFileExistsError, RpcFileNotFoundError, RpcIsADirectoryError, RpcNotADirectoryError, RpcNotEmptyError, \
    RpcPermissionError, RpcResourceTemporarilyUnavailableError, ServerResponseError, SpawnError
from rpcclient.protocol.rpc_bridge import RpcBridge
from rpcclient.protos.rpc_api_pb2 import Argument, MsgId
from rpcclient.protos.rpc_pb2 import ProtocolConstants

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


class ClientEvent(Enum):
    CREATED = auto()
    TERMINATED = auto()


def null_pointer_guard(func: typing.Callable) -> typing.Callable:
    """
    A decorator to prevent dereferencing a null pointer by checking if the given
    address is zero before calling the wrapped function. If the address is zero,
    an ArgumentError is raised.

    Parameters:
        func (Callable): The function to be wrapped by the decorator.

    Returns:
        Callable: The wrapped function with null pointer guard applied.

    Raises:
        ArgumentError: If the 'address' argument is zero.
    """

    @wraps(func)
    def wrapper(self: typing.Any, address: int, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        if address == 0:
            raise ArgumentError('Unable dereference null pointer.')
        return func(self, address, *args, **kwargs)

    return wrapper


class CoreClient:
    """ Main client interface to access the remote rpcserver """
    DEFAULT_ARGV = ['/bin/sh']
    DEFAULT_ENVP = []

    def __init__(self, bridge: RpcBridge, dlsym_global_handle=RTLD_NEXT):
        self._bridge = bridge
        self._old_settings = None
        self._endianness = '<'
        self._dlsym_global_handle = dlsym_global_handle
        self._protocol_lock = threading.Lock()
        self._logger = logging.getLogger(self.__module__)
        self.notifier = EventNotifier()
        self.symbols = SymbolsJar.create(self)

    @subsystem
    def fs(self) -> Fs:
        return Fs(self)

    @subsystem
    def processes(self) -> Processes:
        return Processes(self)

    @subsystem
    def network(self) -> Network:
        return Network(self)

    @subsystem
    def lief(self) -> Lief:
        return Lief(self)

    @subsystem
    def sysctl(self) -> Sysctl:
        return Sysctl(self)

    def info(self):
        """ print information about the current target """
        uname = self.uname
        print('sysname:', uname.sysname)
        print('nodename:', uname.nodename)
        print('release:', uname.release)
        print('version:', uname.version)
        print('machine:', uname.machine)
        print(f'uid: {self.symbols.getuid():d}')
        print(f'gid: {self.symbols.getgid():d}')
        print(f'pid: {self.pid:d}')
        print(f'ppid: {self.symbols.getppid():d}')
        print(f'progname: {self.progname}')

    @cached_property
    def progname(self) -> str:
        """ get the program name from remote """
        # bugfix https://github.com/doronz88/rpc-project/issues/405
        # Default Linux libraries don't expose `getprogname()`, so instead we use the `__progname` global symbol.
        # Tested on both macOS and Ubuntu.
        return self.symbols['__progname'][0].peek_str()

    @cached_property
    def uname(self):
        """ get the utsname struct from remote """
        raise NotImplementedError()

    @property
    def id(self) -> int:
        return self._bridge.client_id

    @property
    def platform(self) -> str:
        return self._bridge.platform

    @property
    def sysname(self) -> str:
        return self._bridge.sysname

    @property
    def arch(self) -> int:
        return self._bridge.arch

    def rpc_call(self, msg_id: int, **kwargs):
        try:
            return self._bridge.rpc_call(msg_id, **kwargs)
        except ConnectionError:
            self.notifier.notify(ClientEvent.TERMINATED, self.id)
            raise
        except ServerResponseError:
            raise

    def dlopen(self, filename: str, mode: int) -> Symbol:
        """ call dlopen() at remote and return its handle. see the man page for more details. """
        return self.symbol(self.rpc_call(MsgId.REQ_DLOPEN, filename=filename, mode=mode).handle)

    def dlclose(self, lib: int) -> int:
        """ call dlclose() at remote and return its handle. see the man page for more details. """
        return self.rpc_call(MsgId.REQ_DLCLOSE, handle=ctypes.c_uint64(lib).value).res

    def dlsym(self, lib: int, symbol_name: str) -> int:
        """ call dlsym() at remote and return its handle. see the man page for more details. """
        return self.rpc_call(MsgId.REQ_DLSYM, handle=ctypes.c_uint64(lib).value, symbol_name=symbol_name).ptr

    @null_pointer_guard
    def call(self, address: int, argv: list[int] = None, return_float64=False, return_float32=False,
             return_raw=False, va_list_index: int = 0xffff) -> typing.Union[float, Symbol, Any]:
        """ call a remote function and retrieve its return value as a Symbol object """
        args = []
        for arg in argv:
            if isinstance(arg, float):
                args.append(Argument(v_double=arg))
            elif isinstance(arg, str):
                args.append(Argument(v_str=arg))
            elif isinstance(arg, int):
                args.append(Argument(v_int=ctypes.c_uint64(arg).value))
            elif isinstance(arg, bytes):
                args.append(Argument(v_bytes=arg))
            elif isinstance(arg, Enum):
                args.append(Argument(v_int=ctypes.c_uint64(arg.value).value))
            else:
                raise ArgumentError()

        ret = self.rpc_call(MsgId.REQ_CALL, address=address, va_list_index=va_list_index, argv=args)
        if ret.HasField('arm_registers'):
            d0 = ret.arm_registers.d0
            if return_float32:
                return ctypes.c_float(d0).value
            if return_float64:
                return d0
            if return_raw:
                return ret.arm_registers
            return self.symbol(ret.arm_registers.x0)
        return self.symbol(ret.return_value)

    @null_pointer_guard
    def peek(self, address: int, size: int) -> bytes:
        """ peek data at the given address """
        try:
            return self.rpc_call(MsgId.REQ_PEEK, address=address, size=size).data
        except ServerResponseError:
            raise ArgumentError()

    @null_pointer_guard
    def poke(self, address: int, data: bytes):
        """ poke data at a given address """
        try:
            return self.rpc_call(MsgId.REQ_POKE, address=address, data=data)
        except ServerResponseError:
            raise ArgumentError()

    def get_dummy_block(self) -> Symbol:
        """ get an address for a stub block containing nothing """
        return self.symbol(self.rpc_call(MsgId.REQ_DUMMY_BLOCK).address)

    def listdir(self, path: str):
        """ get an address for a stub block containing nothing """
        entries = []
        try:
            ret = self.rpc_call(MsgId.REQ_LIST_DIR, path=path)
        except ServerResponseError:
            self.raise_errno_exception(f'failed to listdir: {path}')

        for entry in ret.dir_entries:
            lstat = ProtocolDitentStat(
                errno=entry.lstat.errno1, st_blocks=entry.lstat.st_blocks, st_blksize=entry.lstat.st_blksize,
                st_atime=entry.lstat.st_atime1, st_ctime=entry.lstat.st_ctime1, st_mtime=entry.lstat.st_mtime1,
                st_nlink=entry.lstat.st_nlink, st_mode=entry.lstat.st_mode, st_rdev=entry.lstat.st_rdev,
                st_size=entry.lstat.st_size, st_dev=entry.lstat.st_dev, st_gid=entry.lstat.st_gid,
                st_ino=entry.lstat.st_ino, st_uid=entry.lstat.st_uid)
            stat = ProtocolDitentStat(
                errno=entry.stat.errno1, st_blocks=entry.stat.st_blocks, st_blksize=entry.stat.st_blksize,
                st_atime=entry.stat.st_atime1, st_ctime=entry.stat.st_ctime1, st_mtime=entry.stat.st_mtime1,
                st_nlink=entry.stat.st_nlink, st_mode=entry.stat.st_mode, st_rdev=entry.stat.st_rdev,
                st_size=entry.stat.st_size, st_dev=entry.stat.st_dev, st_gid=entry.stat.st_gid,
                st_ino=entry.stat.st_ino, st_uid=entry.stat.st_uid)
            entries.append(
                ProtocolDirent(d_inode=entry.lstat.st_ino, d_type=entry.d_type, d_name=entry.d_name,
                               lstat=lstat,
                               stat=stat))
        return entries

    def spawn(self, argv: list[str] = None, envp: list[str] = None, stdin: io_or_str = sys.stdin,
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
                error = self.enter_pty_mode(stdin, stdout)
            except Exception:  # noqa: E722
                # this is important to really catch every exception here, even exceptions not inheriting from Exception
                # so the controlling terminal will remain working with its previous settings
                if raw_tty:
                    self._restore_terminal()
                raise

        return SpawnResult(error=error, pid=pid, stdout=stdout)

    def symbol(self, symbol: int):
        """ at a symbol object from a given address """
        return Symbol.create(symbol, self)

    @property
    def errno(self) -> int:
        return self.symbols.errno[0]

    @errno.setter
    def errno(self, value: int) -> None:
        self.symbols.errno[0] = value

    @property
    def last_error(self):
        """ get info about the last occurred error """
        if not self.errno:
            return ''
        err_str = self.symbols.strerror(self.errno).peek_str()
        return f'[{self.errno}] {err_str}'

    @property
    def environ(self) -> list[str]:
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

    @cached_property
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

    def close(self):
        self.rpc_call(MsgId.REQ_CLOSE_CLIENT)
        self.notifier.notify(ClientEvent.TERMINATED, self.id)
        self._bridge.close()

    def shell(self):
        self._logger.disabled = True

        args = ['--rc']
        home_rc = Path('~/.xonshrc').expanduser()
        if home_rc.exists():
            args.append(str(home_rc.expanduser().absolute()))
        args.append(str((Path(__file__).parent / 'xonshrc.py').absolute()))

        XSH.ctx['_client_to_reuse'] = self

        try:
            logging.getLogger('parso.python.diff').disabled = True
            logging.getLogger('parso.cache').disabled = True
            logging.getLogger('asyncio').disabled = True
            xonsh_main(args)
        except SystemExit:
            self._logger.disabled = False

    def _execute(self, argv: list[str], envp: list[str], background=False) -> int:
        try:
            return self.rpc_call(MsgId.REQ_EXEC, background=background, argv=argv, envp=envp).pid
        except ServerResponseError:
            raise SpawnError(f'failed to spawn: {argv}')

    def enter_pty_mode(self, stdin=sys.stdin, stdout=sys.stdout):
        # the socket must be non-blocking for using select()
        sock = self._bridge.sock.raw_socket
        sock.setblocking(False)
        exit_code = None
        try:
            fds = []
            if hasattr(stdin, 'fileno'):
                fds.append(stdin)
            else:
                data = stdin
                if isinstance(data, str):
                    data = data.encode()
                sock.sendall(data)
            fds.append(sock)

            running = True
            while running:
                rlist, _, _ = select(fds, [], [])
                for fd in rlist:
                    if fd == stdin or (stdin is sys.stdin and fd == sys.stdin):
                        if stdin is sys.stdin:
                            buf = os.read(stdin.fileno(), ProtocolConstants.RPC_PTY_BUFFER_SIZE)
                        else:
                            buf = stdin.read(ProtocolConstants.RPC_PTY_BUFFER_SIZE)
                            if isinstance(buf, str):
                                buf = buf.encode()
                        if buf:
                            sock.sendall(buf)
                    elif fd == sock:
                        try:
                            response = self._bridge.sock.rpc_msg_recv_pty()
                        except ConnectionResetError:
                            print('Bye. 👋')
                            running = False
                            break
                        msg_type = response.WhichOneof('type')
                        if msg_type == 'buffer':
                            stdout.write(response.buffer.decode())
                            if hasattr(stdout, 'flush'):
                                stdout.flush()
                        elif msg_type == 'exit_code':
                            exit_code = response.exit_code
                            running = False
                            break
        finally:
            sock.setblocking(True)
        return exit_code

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

    def capture_fd(self, fd: int, sock_buf_size: Optional[int] = None) -> CaptureFD:
        """
        Get a context manager, capturing output to `fd`. Read from it using the `read()` method

        sock_buf_size is required for captures above 6KB, as any write above this value would block until a read is performed.

        :param fd: FD to capture
        :param sock_buf_size: Buffer size for the capture socket, if not specified, default value is used.
        :return: CaptureFD object
        """
        return CaptureFD(self, fd, sock_buf_size)

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.pid} | {self.progname}>'
