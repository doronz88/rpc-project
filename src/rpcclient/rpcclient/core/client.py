import abc
import asyncio
import ctypes
import dataclasses
import logging
import os
import sys
import threading
from collections.abc import AsyncGenerator, Callable, Coroutine, Iterable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from enum import Enum, auto
from functools import cached_property, wraps
from pathlib import Path, PurePath
from select import select
from typing import (
    IO,
    Any,
    ClassVar,
    Concatenate,
    Generic,
    Literal,
    NamedTuple,
    ParamSpec,
    TextIO,
    TypeAlias,
    TypeVar,
    cast,
)
from typing_extensions import Buffer, Self, assert_never

import zyncio
from construct import Container
from xonsh.built_ins import XSH
from xonsh.main import main as xonsh_main

from rpcclient.clients.darwin.consts import BLOCK_IS_GLOBAL
from rpcclient.core.capture_fd import CaptureFD
from rpcclient.core.structs.consts import (
    EAGAIN,
    ECONNREFUSED,
    EEXIST,
    EISDIR,
    ENOENT,
    ENOTDIR,
    ENOTEMPTY,
    EPERM,
    EPIPE,
    RTLD_NEXT,
)
from rpcclient.core.structs.generic import block_descriptor, block_literal
from rpcclient.core.subsystems.decorator import subsystem
from rpcclient.core.subsystems.fs import Fs
from rpcclient.core.subsystems.lief import Lief
from rpcclient.core.subsystems.network import Network
from rpcclient.core.subsystems.processes import Processes
from rpcclient.core.subsystems.sysctl import Sysctl
from rpcclient.core.symbol import BaseSymbol
from rpcclient.core.symbols_jar import (
    AsyncSymbolT_co,
    LazySymbol,
    SymbolsJar,
    SymbolT,
    SymbolT_co,
)
from rpcclient.event_notifier import EventNotifier
from rpcclient.exceptions import (
    ArgumentError,
    BadReturnValueError,
    RpcBrokenPipeError,
    RpcConnectionRefusedError,
    RpcFileExistsError,
    RpcFileNotFoundError,
    RpcIsADirectoryError,
    RpcNotADirectoryError,
    RpcNotEmptyError,
    RpcPermissionError,
    RpcResourceTemporarilyUnavailableError,
    ServerResponseError,
    SpawnError,
)
from rpcclient.protocol.rpc_bridge import AsyncRpcBridge, SyncRpcBridge
from rpcclient.protos.rpc_api_pb2 import Argument, MsgId
from rpcclient.protos.rpc_pb2 import ProtocolConstants


tty_support = False
try:
    import termios
    import tty

    tty_support = True
except ImportError:
    logging.warning("termios not available on your system. some functionality may not work as expected")

StrOrIO = TypeVar("StrOrIO", IO, str)


class SpawnResult(NamedTuple):
    error: object
    pid: int
    stdout: TextIO | None


INVALID_PID = 0xFFFFFFFF
CHUNK_SIZE = 1024

USAGE = """
Welcome to the rpcclient interactive shell! You interactive shell for controlling the remote rpcserver.
Feel free to use the following globals:

🌍 p - the injected process
🌍 symbols - process global symbols

Have a nice flight ✈️!
Starting an IPython shell... 🐍
"""


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


SelfT = TypeVar("SelfT")
P = ParamSpec("P")
ReturnT = TypeVar("ReturnT")


def null_pointer_guard(
    func: Callable[Concatenate[SelfT, int, P], ReturnT],
) -> Callable[Concatenate[SelfT, int, P], ReturnT]:
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
    def wrapper(self: SelfT, /, address: int, *args: P.args, **kwargs: P.kwargs) -> ReturnT:
        if address == 0:
            raise ArgumentError("Unable dereference null pointer.")
        return func(self, address, *args, **kwargs)

    return wrapper


RemoteCallArg: TypeAlias = LazySymbol | float | str | int | bytes | Enum | PurePath


class BaseCoreClient(Generic[SymbolT_co], zyncio.ZyncBase, abc.ABC):
    """Main client interface to access the remote rpcserver"""

    DEFAULT_ARGV: ClassVar[list[str]] = ["/bin/sh"]
    DEFAULT_ENVP: ClassVar[list[str]] = []

    def __init__(self, bridge: SyncRpcBridge | AsyncRpcBridge, dlsym_global_handle: int = RTLD_NEXT) -> None:
        self._bridge: SyncRpcBridge | AsyncRpcBridge = bridge
        self._old_settings = None
        self._endianness: Literal["<", ">"] = "<"
        self._dlsym_global_handle: int = dlsym_global_handle
        self._logger: logging.Logger = logging.getLogger(self.__module__)
        self.notifier: EventNotifier = EventNotifier()
        self.pre_rpc_call_hooks: list[Callable[[], Coroutine[Any, Any, object]]] = []

    @abc.abstractmethod
    def _acquire_protocol_lock(self) -> AbstractAsyncContextManager[None]: ...

    @cached_property
    def symbols(self) -> SymbolsJar[SymbolT_co]:
        return SymbolsJar(self)

    @cached_property
    def null(self) -> SymbolT_co:
        return self.symbol(0)

    @zyncio.zclassmethod
    @classmethod
    async def create(cls, bridge: SyncRpcBridge | AsyncRpcBridge) -> Self:
        return cls(bridge)

    @subsystem
    @abc.abstractmethod
    def fs(self) -> Fs[Self]: ...

    @subsystem
    def processes(self) -> Processes[Self]:
        return Processes(self)

    @subsystem
    def network(self) -> Network[Self]:
        return Network(self)

    @subsystem
    def lief(self) -> Lief[Self]:
        return Lief(self)

    @subsystem
    def sysctl(self) -> Sysctl[Self]:
        return Sysctl(self)

    @zyncio.zmethod
    async def info(self) -> None:
        """print information about the current target"""
        uname = await self.get_uname.z()
        print("sysname:", uname.sysname)
        print("nodename:", uname.nodename)
        print("release:", uname.release)
        print("version:", uname.version)
        print("machine:", uname.machine)
        print(f"uid: {(await self.symbols.getuid.z()):d}")
        print(f"gid: {(await self.symbols.getgid.z()):d}")
        print(f"pid: {await self.get_pid.z():d}")
        print(f"ppid: {(await self.symbols.getppid.z()):d}")
        print(f"progname: {await self.get_progname.z()}")

    _cached_progname: str | None = None

    @zyncio.zmethod
    async def get_progname(self) -> str:
        """get the program name from remote"""
        if self._cached_progname is None:
            # bugfix https://github.com/doronz88/rpc-project/issues/405
            # Default Linux libraries don't expose `getprogname()`, so instead we use the `__progname` global symbol.
            # Tested on both macOS and Ubuntu.
            self._cached_progname = await (await self.symbols["__progname"].getindex(0)).peek_str.z()

        return self._cached_progname

    @zyncio.zproperty
    async def progname(self) -> str:
        """get the program name from remote"""
        return await self.get_progname.z()

    @zyncio.zmethod
    @abc.abstractmethod
    async def get_uname(self) -> Container:
        """get the utsname struct from remote"""

    @zyncio.zproperty
    async def uname(self) -> Container:
        """get the utsname struct from remote"""
        return await self.get_uname.z()

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

    @zyncio.zmethod
    async def rpc_call(self, msg_id: int, **kwargs: Any) -> Any:
        # Pop all hooks here, to prevent hooks from running out of order due to recursion.
        hooks, self.pre_rpc_call_hooks[:] = self.pre_rpc_call_hooks[::-1], []
        try:
            while hooks:
                await hooks.pop()()
        finally:
            # In case of failure, re-insert the remaining hooks.
            if hooks:
                self.pre_rpc_call_hooks[:0] = hooks

        try:
            return await self._bridge.rpc_call(msg_id, **kwargs)
        except ConnectionError:
            self.notifier.notify(ClientEvent.TERMINATED, self.id)
            raise
        except ServerResponseError:
            raise

    @zyncio.zmethod
    async def dlopen(self, filename: str, mode: int) -> SymbolT_co:
        """Load a shared library on the remote host and return its handle."""
        return self.symbol((await self.rpc_call.z(MsgId.REQ_DLOPEN, filename=filename, mode=mode)).handle)

    @zyncio.zmethod
    async def dlclose(self, lib: int) -> int:
        """Close a previously opened remote library handle."""
        return (await self.rpc_call.z(MsgId.REQ_DLCLOSE, handle=ctypes.c_uint64(lib).value)).res

    @zyncio.zmethod
    async def dlsym(self, lib: int, symbol_name: str) -> int:
        """Resolve a symbol name in a remote library handle and return its address.

        Runs and pops any hooks in `self.pre_dlsym_hooks` first.
        """
        return (await self.rpc_call.z(MsgId.REQ_DLSYM, handle=ctypes.c_uint64(lib).value, symbol_name=symbol_name)).ptr

    @zyncio.zmethod
    @null_pointer_guard
    async def call(
        self,
        address: int,
        argv: Iterable[RemoteCallArg] = (),
        return_float64: bool = False,
        return_float32: bool = False,
        return_raw: bool = False,
        va_list_index: int | None = None,
    ) -> float | SymbolT_co | Any:
        """call a remote function and retrieve its return value as a Symbol object"""
        if va_list_index is None:
            va_list_index = 0xFFFF

        args: list[Argument] = []
        for arg in argv:
            if isinstance(arg, LazySymbol):
                arg = int(await arg.resolve())

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
            elif isinstance(arg, PurePath):
                args.append(Argument(v_str=str(arg)))
            else:
                assert_never(arg)
                raise ArgumentError(f"Can't serialize object of type {type(arg).__name__}")

        ret = await self.rpc_call.z(MsgId.REQ_CALL, address=address, va_list_index=va_list_index, argv=args)
        if ret.HasField("arm_registers"):
            d0 = ret.arm_registers.d0
            if return_float32:
                return ctypes.c_float(d0).value
            if return_float64:
                return d0
            if return_raw:
                return ret.arm_registers
            return self.symbol(ret.arm_registers.x0)
        return self.symbol(ret.return_value)

    @zyncio.zmethod
    @null_pointer_guard
    async def peek(self, address: int, size: int) -> bytes:
        """peek data at the given address"""
        try:
            return (await self.rpc_call.z(MsgId.REQ_PEEK, address=address, size=size)).data
        except ServerResponseError as e:
            raise ArgumentError() from e

    @zyncio.zmethod
    @null_pointer_guard
    async def poke(self, address: int, data: bytes) -> Any:
        """poke data at a given address"""
        try:
            return await self.rpc_call.z(MsgId.REQ_POKE, address=address, data=data)
        except ServerResponseError as e:
            raise ArgumentError() from e

    @zyncio.zmethod
    async def get_dummy_block(self) -> SymbolT_co:
        """Get an address for a stub block containing nothing"""
        block_size = block_literal.sizeof()
        desc_size = block_descriptor.sizeof()

        descriptor = await self.symbols.malloc.z(desc_size)
        await descriptor.poke.z(block_descriptor.build({"reserved": 0, "size": block_size}))

        block = await self.symbols.malloc.z(block_size)
        await block.poke.z(
            block_literal.build({
                "isa": await self.symbols._NSConcreteGlobalBlock.resolve(),
                "flags": BLOCK_IS_GLOBAL,
                "reserved": 0,
                "invoke": await self.symbols.getpid.resolve(),
                "descriptor": descriptor,
            }),
        )

        return block

    @zyncio.zmethod
    async def listdir(self, path: str | PurePath) -> list[ProtocolDirent]:
        """get an address for a stub block containing nothing"""
        entries: list[ProtocolDirent] = []
        try:
            ret = await self.rpc_call.z(MsgId.REQ_LIST_DIR, path=str(path))
        except ServerResponseError:
            await self.raise_errno_exception.z(f"failed to listdir: {path}")

        for entry in ret.dir_entries:
            lstat = ProtocolDitentStat(
                errno=entry.lstat.errno1,
                st_blocks=entry.lstat.st_blocks,
                st_blksize=entry.lstat.st_blksize,
                st_atime=entry.lstat.st_atime1,
                st_ctime=entry.lstat.st_ctime1,
                st_mtime=entry.lstat.st_mtime1,
                st_nlink=entry.lstat.st_nlink,
                st_mode=entry.lstat.st_mode,
                st_rdev=entry.lstat.st_rdev,
                st_size=entry.lstat.st_size,
                st_dev=entry.lstat.st_dev,
                st_gid=entry.lstat.st_gid,
                st_ino=entry.lstat.st_ino,
                st_uid=entry.lstat.st_uid,
            )
            stat = ProtocolDitentStat(
                errno=entry.stat.errno1,
                st_blocks=entry.stat.st_blocks,
                st_blksize=entry.stat.st_blksize,
                st_atime=entry.stat.st_atime1,
                st_ctime=entry.stat.st_ctime1,
                st_mtime=entry.stat.st_mtime1,
                st_nlink=entry.stat.st_nlink,
                st_mode=entry.stat.st_mode,
                st_rdev=entry.stat.st_rdev,
                st_size=entry.stat.st_size,
                st_dev=entry.stat.st_dev,
                st_gid=entry.stat.st_gid,
                st_ino=entry.stat.st_ino,
                st_uid=entry.stat.st_uid,
            )
            entries.append(
                ProtocolDirent(
                    d_inode=entry.lstat.st_ino,
                    d_type=entry.d_type,
                    d_name=entry.d_name,
                    lstat=lstat,
                    stat=stat,
                )
            )
        return entries

    @zyncio.zmethod
    async def spawn(
        self,
        argv: list[str] | None = None,
        envp: list[str] | None = None,
        stdin: StrOrIO = sys.stdin,
        stdout=sys.stdout,
        raw_tty=False,
        background=False,
    ) -> SpawnResult:
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

        async with self._acquire_protocol_lock():
            pid = await self._execute(argv, envp, background=background)
            self._logger.info(f"shell process started as pid: {pid}")

            if background:
                return SpawnResult(error=None, pid=pid, stdout=None)

            if raw_tty:
                self._prepare_terminal()
            try:
                error = await self.enter_pty_mode.z(stdin, stdout)
            except Exception:
                # this is important to really catch every exception here, even exceptions not inheriting from Exception
                # so the controlling terminal will remain working with its previous settings
                if raw_tty:
                    self._restore_terminal()
                raise

        return SpawnResult(error=error, pid=pid, stdout=stdout)

    @abc.abstractmethod
    def symbol(self, symbol: int) -> SymbolT_co:
        """Get a symbol object from a given address"""

    @zyncio.zmethod
    async def get_errno(self) -> int:
        return await self.symbols.errno.getindex(0)

    @zyncio.zmethod
    async def set_errno(self, value: int) -> None:
        await self.symbols.errno.setindex(0, value)

    @zyncio.zproperty
    async def _get_errno(self) -> int:
        return await self.get_errno.z()

    @_get_errno.setter
    async def errno(self, value: int) -> None:
        await self.set_errno.z(value)

    @zyncio.zmethod
    async def get_last_error(self) -> str:
        """get info about the last occurred error"""
        if not (errno := await self.get_errno.z()):
            return ""
        err_str_ptr = await self.symbols.strerror.z(errno)
        err_str = await err_str_ptr.peek_str.z()
        return f"[{errno}] {err_str}"

    @zyncio.zproperty
    async def environ(self) -> list[str]:
        result = []
        environ = await self.symbols.environ.getindex(0)
        i = 0
        while var_ptr := await environ.getindex(i):
            result.append(await var_ptr.peek_str.z())
            i += 1
        return result

    @zyncio.zmethod
    async def setenv(self, name: str, value: str) -> None:
        """set process environment variable"""
        await (await self.symbols.setenv.resolve()).call(name, value)

    @zyncio.zmethod
    async def getenv(self, name: str) -> str | None:
        """get process environment variable"""
        value = await self.symbols.getenv.z(name)
        if not isinstance(value, BaseSymbol) or not value:
            return None
        return await value.peek_str.z()

    _cached_pid: int | None = None

    @zyncio.zmethod
    async def get_pid(self) -> int:
        if self._cached_pid is None:
            self._cached_pid = int(await self.symbols.getpid.z())

        return self._cached_pid

    @zyncio.zproperty
    async def pid(self) -> int:
        return await self.get_pid.z()

    @zyncio.zcontextmanagermethod
    async def safe_calloc(self, size: int) -> AsyncGenerator[SymbolT_co]:
        async with self.safe_malloc.z(size) as x:
            await x.poke.z(b"\x00" * size)
            yield x

    @zyncio.zcontextmanagermethod
    async def safe_malloc(self, size: int) -> AsyncGenerator[SymbolT_co]:
        ptr = cast(SymbolT_co, await self.symbols.malloc.z(size))
        async with self.freeing.z(ptr) as x:
            yield x

    @zyncio.zcontextmanagermethod
    async def freeing(self, symbol: SymbolT) -> AsyncGenerator[SymbolT]:
        try:
            yield symbol
        finally:
            if symbol:
                await self.symbols.free.z(symbol)

    @zyncio.zmethod
    async def close(self) -> None:
        await self.rpc_call.z(MsgId.REQ_CLOSE_CLIENT)
        self.notifier.notify(ClientEvent.TERMINATED, self.id)
        self._bridge.close()

    def shell(self) -> None:
        self._logger.disabled = True

        args = ["--rc"]
        args.append(str((Path(__file__).parent / "xonshrc.py").absolute()))

        XSH.ctx["_client_to_reuse"] = self

        try:
            logging.getLogger("parso.python.diff").disabled = True
            logging.getLogger("parso.cache").disabled = True
            logging.getLogger("asyncio").disabled = True
            xonsh_main(args)
        except SystemExit:
            self._logger.disabled = False

    async def _execute(self, argv: list[str], envp: list[str], background=False) -> int:
        try:
            return (await self.rpc_call.z(MsgId.REQ_EXEC, background=background, argv=argv, envp=envp)).pid
        except ServerResponseError as e:
            raise SpawnError(f"failed to spawn: {argv}") from e

    @zyncio.zmethod
    async def enter_pty_mode(self, stdin=sys.stdin, stdout=sys.stdout):
        # the socket must be non-blocking for using select()
        sock = self._bridge.sock.raw_socket
        blocking = sock.getblocking()
        sock.setblocking(False)
        exit_code = None
        try:
            fds = []
            if hasattr(stdin, "fileno"):
                fds.append(stdin)
            else:
                data = stdin
                if isinstance(data, str):
                    data = data.encode()
                sock.sendall(cast(Buffer, data))
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
                            response = await self._bridge.sock.rpc_msg_recv_pty.z()
                        except ConnectionResetError:
                            print("Bye. 👋")
                            running = False
                            break
                        msg_type = response.WhichOneof("type")
                        if msg_type == "buffer":
                            stdout.write(response.buffer.decode())
                            if hasattr(stdout, "flush"):
                                stdout.flush()
                        elif msg_type == "exit_code":
                            exit_code = response.exit_code
                            running = False
                            break
        finally:
            sock.setblocking(blocking)
        return exit_code

    def _restore_terminal(self) -> None:
        if not tty_support:
            return
        assert self._old_settings is not None
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_settings)  # pyright: ignore[reportPossiblyUnboundVariable]

    def _prepare_terminal(self):
        if not tty_support:
            return
        fd = sys.stdin
        self._old_settings = termios.tcgetattr(fd)  # pyright: ignore[reportPossiblyUnboundVariable]
        tty.setraw(fd)  # pyright: ignore[reportPossiblyUnboundVariable]

    @zyncio.zmethod
    async def raise_errno_exception(self, message: str):
        message += f" ({await self.get_last_error.z()})"
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
        exception = exceptions.get(await self.get_errno.z())
        if exception:
            raise exception(message)
        raise BadReturnValueError(message)

    def capture_fd(self, fd: int, sock_buf_size: int | None = None) -> CaptureFD[SymbolT_co]:
        """
        Get a context manager, capturing output to `fd`. Read from it using the `read()` method

        sock_buf_size is required for captures above 6KB, as any write above this value would block until a read is performed.

        :param fd: FD to capture
        :param sock_buf_size: Buffer size for the capture socket, if not specified, default value is used.
        :return: CaptureFD object
        """
        return CaptureFD(self, fd, sock_buf_size)

    def __repr__(self) -> str:
        if zyncio.is_sync(self):
            progname = self.progname
            pid = self.pid
        else:
            pid = self._cached_pid if self._cached_pid is not None else "?"
            progname = self._cached_progname if self._cached_progname is not None else "?"
        return f"<{self.__class__.__name__}: {pid} | {progname}>"


class CoreClient(zyncio.SyncMixin, BaseCoreClient[SymbolT_co]):
    def __init__(self, bridge: SyncRpcBridge | AsyncRpcBridge, dlsym_global_handle: int = RTLD_NEXT) -> None:
        self._protocol_lock: threading.Lock = threading.Lock()
        super().__init__(bridge, dlsym_global_handle)

    @asynccontextmanager
    async def _acquire_protocol_lock(self) -> AsyncGenerator[None]:
        with self._protocol_lock:
            yield

    @property
    def last_error(self) -> str:
        return self.get_last_error()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class AsyncCoreClient(zyncio.AsyncMixin, BaseCoreClient[AsyncSymbolT_co]):
    def __init__(self, bridge: SyncRpcBridge | AsyncRpcBridge, dlsym_global_handle: int = RTLD_NEXT) -> None:
        self._protocol_lock: asyncio.Lock = asyncio.Lock()
        super().__init__(bridge, dlsym_global_handle)

    @asynccontextmanager
    async def _acquire_protocol_lock(self) -> AsyncGenerator[None]:
        async with self._protocol_lock:
            yield

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
