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
from pathlib import Path
from select import select
from typing import Any, Optional

from cached_property import cached_property
from xonsh.built_ins import XSH
from xonsh.main import main as xonsh_main

from rpcclient.core.capture_fd import CaptureFD
from rpcclient.core.protobuf_bridge import Argument, CmdCall, CmdDlclose, CmdDlopen, CmdDlsym, CmdDummyBlock, CmdExec, \
    CmdListDir, CmdPeek, CmdPoke, Response
from rpcclient.core.protosocket import ProtoSocket
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


class CoreClient:
    """ Main client interface to access remote rpcserver """
    DEFAULT_ARGV = ['/bin/sh']
    DEFAULT_ENVP = []

    def __init__(self, cid: int, sock: ProtoSocket, sysname: str, arch, server_type: str = 'core',
                 dlsym_global_handle=RTLD_NEXT):
        self._arch = arch
        self._sock = sock
        self._old_settings = None
        self._endianness = '<'
        self._sysname = sysname
        self._dlsym_global_handle = dlsym_global_handle
        self._protocol_lock = threading.Lock()
        self._logger = logging.getLogger(self.__module__)
        self.notifier = EventNotifier()
        self.symbols = SymbolsJar.create(self)
        self.type = server_type
        self.id = cid

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
    def progname(self):
        return self.symbols.getprogname().peek_str()

    @cached_property
    def uname(self):
        """ get the utsname struct from remote """
        raise NotImplementedError()

    @cached_property
    def arch(self):
        """ get remote arch """
        return self._arch

    def send_recv(self, command):
        try:
            return self._sock.send_recv(command, self.id)
        except ConnectionError:
            self.notifier.notify(ClientEvent.TERMINATED, self.id)

    def dlopen(self, filename: str, mode: int) -> Symbol:
        """ call dlopen() at remote and return its handle. see the man page for more details. """
        command = CmdDlopen(filename=filename, mode=mode)
        response = self.send_recv(command)
        return self.symbol(response.handle)

    def dlclose(self, lib: int):
        """ call dlclose() at remote and return its handle. see the man page for more details. """
        command = CmdDlclose(handle=ctypes.c_uint64(lib).value)
        response = self.send_recv(command)
        return response.res

    def dlsym(self, lib: int, symbol_name: str):
        """ call dlsym() at remote and return its handle. see the man page for more details. """
        command = CmdDlsym(handle=ctypes.c_uint64(lib).value, symbol_name=symbol_name)
        response = self.send_recv(command)
        return response.ptr

    def call(self, address: int, argv: list[int] = None, return_float64=False, return_float32=False,
             return_raw=False, va_list_index: int = 0xffff) -> typing.Union[float, Symbol, Any]:
        """ call a remote function and retrieve its return value as Symbol object """
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

        command = CmdCall(address=address, va_list_index=va_list_index, argv=args)
        response = self.send_recv(command)
        if response.HasField('arm_registers'):
            double = response.arm_registers.d0
            if return_float32:
                return ctypes.c_float(double).value
            if return_float64:
                return double
            if return_raw:
                return response.arm_registers
            return self.symbol(response.arm_registers.x0)
        return self.symbol(response.return_value)

    def peek(self, address: int, size: int) -> bytes:
        """ peek data at given address """
        command = CmdPeek(address=address, size=size)
        try:
            return self.send_recv(command).data
        except ServerResponseError:
            raise ArgumentError()

    def poke(self, address: int, data: bytes):
        """ poke data at given address """
        command = CmdPoke(address=address, data=data)
        try:
            self.send_recv(command)
        except ServerResponseError:
            raise ArgumentError()

    def get_dummy_block(self) -> Symbol:
        """ get an address for a stub block containing nothing """
        command = CmdDummyBlock()
        response = self.send_recv(command)
        return self.symbol(response.address)

    def listdir(self, filename: str):
        """ get an address for a stub block containing nothing """
        command = CmdListDir(path=filename)
        entries = []
        try:
            response = self.send_recv(command)
        except ServerResponseError:
            self.raise_errno_exception(f'failed to listdir: {filename}')

        for entry in response.dir_entries:
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
                # the socket must be non-blocking for using select()
                self._sock.raw_socket.setblocking(False)
                error = self._execution_loop(stdin, stdout)
            except Exception:  # noqa: E722
                # this is important to really catch every exception here, even exceptions not inheriting from Exception
                # so the controlling terminal will remain working with its previous settings
                if raw_tty:
                    self._restore_terminal()
                raise
            finally:
                self._sock.raw_socket.setblocking(True)

        if raw_tty:
            self._restore_terminal()

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
        self._sock.close()
        self.notifier.notify(ClientEvent.TERMINATED, self.id)

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
        command = CmdExec(background=background, argv=argv, envp=envp)
        try:
            return self.send_recv(command).pid
        except ServerResponseError:
            raise SpawnError(f'failed to spawn: {argv}')

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

    def _execution_loop(self, stdin: io_or_str = sys.stdin, stdout=sys.stdout):
        """
        if stdin is a file object, we need to select between the fds and give higher priority to stdin.
        otherwise, we can simply write all stdin contents directly to the process
        """
        fds = []
        raw_socket = self._sock.raw_socket
        if hasattr(stdin, 'fileno'):
            fds.append(stdin)
        else:
            # assume it's just raw bytes
            raw_socket.sendall(stdin.encode())
        fds.append(raw_socket)

        while True:
            response = Response()
            rlist, _, _ = select(fds, [], [])

            for fd in rlist:
                if fd == sys.stdin:
                    if stdin == sys.stdin:
                        buf = os.read(stdin.fileno(), CHUNK_SIZE)
                    else:
                        buf = stdin.read(CHUNK_SIZE)
                    raw_socket.sendall(buf)
                elif fd == raw_socket:
                    try:
                        size, buf = self._sock._receive()
                        response.ParseFromString(buf)
                    except ConnectionResetError:
                        print('Bye. 👋')
                        return
                    _type = response.exec_chunk.WhichOneof('type')
                    if _type == 'buffer':
                        stdout.write(response.exec_chunk.buffer.decode())
                        stdout.flush()
                    elif _type == 'exit_code':
                        return response.exec_chunk.exit_code

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
