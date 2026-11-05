# Core client

## CoreClient

## rpcclient.core.client.CoreClient

Bases: `Generic[SymbolT_co]`, `ABC`

Main client interface to access the remote rpcserver

Source code in `src/rpcclient/rpcclient/core/client.py`

```
class CoreClient(Generic[SymbolT_co], abc.ABC):
    """Main client interface to access the remote rpcserver"""

    DEFAULT_ARGV: ClassVar[list[str]] = ["/bin/sh"]
    DEFAULT_ENVP: ClassVar[list[str]] = []

    def __init__(self, bridge: RpcBridge, dlsym_global_handle: int = RTLD_NEXT) -> None:
        self._bridge: RpcBridge = bridge
        self._old_settings = None
        self._endianness: Literal["<", ">"] = "<"
        self._dlsym_global_handle: int = dlsym_global_handle
        self._logger: logging.Logger = logging.getLogger(self.__module__)
        self.notifier: EventNotifier = EventNotifier()
        self.pre_rpc_call_hooks: list[Callable[[], Coroutine[Any, Any, object]]] = []
        self._protocol_lock: asyncio.Lock = asyncio.Lock()

    @asynccontextmanager
    async def _acquire_protocol_lock(self) -> AsyncGenerator[None]:
        async with self._protocol_lock:
            yield

    @cached_property
    def symbols(self) -> SymbolsJar[SymbolT_co]:
        return SymbolsJar(self)

    @cached_property
    def null(self) -> SymbolT_co:
        return self.symbol(0)

    @classmethod
    async def create(cls, bridge: RpcBridge) -> Self:
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

    @subsystem
    def webdav(self) -> WebDav[Self]:
        return WebDav(self)

    async def info(self) -> None:
        """print information about the current target"""
        uname = await self.get_uname()
        print("sysname:", uname.sysname)
        print("nodename:", uname.nodename)
        print("release:", uname.release)
        print("version:", uname.version)
        print("machine:", uname.machine)
        print(f"uid: {(await self.symbols.getuid()):d}")
        print(f"gid: {(await self.symbols.getgid()):d}")
        print(f"pid: {await self.get_pid():d}")
        print(f"ppid: {(await self.symbols.getppid()):d}")
        print(f"progname: {await self.get_progname()}")

    _cached_progname: str | None = None

    async def get_progname(self) -> str:
        """get the program name from remote"""
        if self._cached_progname is None:
            # bugfix https://github.com/doronz88/rpc-project/issues/405
            # Default Linux libraries don't expose `getprogname()`, so instead we use the `__progname` global symbol.
            # Tested on both macOS and Ubuntu.
            self._cached_progname = await (await self.symbols["__progname"].getindex(0)).peek_str()

        return self._cached_progname

    async def progname(self) -> str:
        """get the program name from remote"""
        return await self.get_progname()

    @abc.abstractmethod
    async def get_uname(self) -> Container:
        """get the utsname struct from remote"""

    async def uname(self) -> Container:
        """get the utsname struct from remote"""
        return await self.get_uname()

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
            self._bridge.close()
            raise
        except ServerResponseError:
            raise

    async def dlopen(self, filename: str, mode: int) -> SymbolT_co:
        """Load a shared library on the remote host and return its handle."""
        return self.symbol((await self.rpc_call(MsgId.REQ_DLOPEN, filename=filename, mode=mode)).handle)

    async def dlclose(self, lib: int) -> int:
        """Close a previously opened remote library handle."""
        return (await self.rpc_call(MsgId.REQ_DLCLOSE, handle=ctypes.c_uint64(lib).value)).res

    async def dlsym(self, lib: int, symbol_name: str) -> int:
        """Resolve a symbol name in a remote library handle and return its address.

        Runs and pops any hooks in `self.pre_dlsym_hooks` first.
        """
        return (await self.rpc_call(MsgId.REQ_DLSYM, handle=ctypes.c_uint64(lib).value, symbol_name=symbol_name)).ptr

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

        ret = await self.rpc_call(MsgId.REQ_CALL, address=address, va_list_index=va_list_index, argv=args)
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

    @null_pointer_guard
    async def peek(self, address: int, size: int) -> bytes:
        """peek data at the given address"""
        try:
            return (await self.rpc_call(MsgId.REQ_PEEK, address=address, size=size)).data
        except ServerResponseError as e:
            raise ArgumentError() from e

    @null_pointer_guard
    async def poke(self, address: int, data: bytes) -> Any:
        """poke data at a given address"""
        try:
            return await self.rpc_call(MsgId.REQ_POKE, address=address, data=data)
        except ServerResponseError as e:
            raise ArgumentError() from e

    async def get_dummy_block(self) -> SymbolT_co:
        """Get an address for a stub block containing nothing"""
        block_size = block_literal.sizeof()
        desc_size = block_descriptor.sizeof()

        descriptor = await self.symbols.malloc(desc_size)
        await descriptor.poke(block_descriptor.build({"reserved": 0, "size": block_size}))

        block = await self.symbols.malloc(block_size)
        await block.poke(
            block_literal.build({
                "isa": await self.symbols._NSConcreteGlobalBlock.resolve(),
                "flags": BLOCK_IS_GLOBAL,
                "reserved": 0,
                "invoke": await self.symbols.getpid.resolve(),
                "descriptor": descriptor,
            }),
        )

        return block

    async def listdir(self, path: str | PurePath) -> list[ProtocolDirent]:
        """get an address for a stub block containing nothing"""
        entries: list[ProtocolDirent] = []
        try:
            ret = await self.rpc_call(MsgId.REQ_LIST_DIR, path=str(path))
        except ServerResponseError:
            await self.raise_errno_exception(f"failed to listdir: {path}")

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
                error = await self.enter_pty_mode(stdin, stdout)
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

    async def get_errno(self) -> int:
        return await self.symbols.errno.getindex(0)

    async def set_errno(self, value: int) -> None:
        await self.symbols.errno.setindex(0, value)

    async def get_last_error(self) -> str:
        """get info about the last occurred error"""
        if not (errno := await self.get_errno()):
            return ""
        err_str_ptr = await self.symbols.strerror(errno)
        err_str = await err_str_ptr.peek_str()
        return f"[{errno}] {err_str}"

    async def environ(self) -> list[str]:
        result = []
        environ = await self.symbols.environ.getindex(0)
        i = 0
        while var_ptr := await environ.getindex(i):
            result.append(await var_ptr.peek_str())
            i += 1
        return result

    async def setenv(self, name: str, value: str) -> None:
        """set process environment variable"""
        await (await self.symbols.setenv.resolve()).call(name, value)

    async def getenv(self, name: str) -> str | None:
        """get process environment variable"""
        value = await self.symbols.getenv(name)
        if not isinstance(value, Symbol) or not value:
            return None
        return await value.peek_str()

    _cached_pid: int | None = None

    async def get_pid(self) -> int:
        if self._cached_pid is None:
            self._cached_pid = int(await self.symbols.getpid())

        return self._cached_pid

    async def pid(self) -> int:
        return await self.get_pid()

    @asynccontextmanager
    async def safe_calloc(self, size: int) -> AsyncGenerator[SymbolT_co]:
        async with self.safe_malloc(size) as x:
            await x.poke(b"\x00" * size)
            yield x

    @asynccontextmanager
    async def safe_malloc(self, size: int) -> AsyncGenerator[SymbolT_co]:
        ptr = cast(SymbolT_co, await self.symbols.malloc(size))
        async with self.freeing(ptr) as x:
            yield x

    @asynccontextmanager
    async def freeing(self, symbol: SymbolT) -> AsyncGenerator[SymbolT]:
        try:
            yield symbol
        finally:
            if symbol:
                await self.symbols.free(symbol)

    async def close(self) -> None:
        try:
            await self.rpc_call(MsgId.REQ_CLOSE_CLIENT)
        finally:
            self.notifier.notify(ClientEvent.TERMINATED, self.id)
            self._bridge.close()

    async def _execute(self, argv: list[str], envp: list[str], background=False) -> int:
        try:
            return (await self.rpc_call(MsgId.REQ_EXEC, background=background, argv=argv, envp=envp)).pid
        except ServerResponseError as e:
            raise SpawnError(f"failed to spawn: {argv}") from e

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
                            response = await self._bridge.sock.rpc_msg_recv_pty()
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

    async def raise_errno_exception(self, message: str):
        message += f" ({await self.get_last_error()})"
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
        exception = exceptions.get(await self.get_errno())
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

    async def last_error(self) -> str:
        return await self.get_last_error()

    def shell(self) -> None:
        from xonsh.built_ins import XSH
        from xonsh.main import main as xonsh_main

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

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def __repr__(self) -> str:
        pid = self._cached_pid if self._cached_pid is not None else "?"
        progname = self._cached_progname if self._cached_progname is not None else "?"
        return f"<{self.__class__.__name__}: {pid} | {progname}>"
```

### info

```
info() -> None
```

print information about the current target

Source code in `src/rpcclient/rpcclient/core/client.py`

```
async def info(self) -> None:
    """print information about the current target"""
    uname = await self.get_uname()
    print("sysname:", uname.sysname)
    print("nodename:", uname.nodename)
    print("release:", uname.release)
    print("version:", uname.version)
    print("machine:", uname.machine)
    print(f"uid: {(await self.symbols.getuid()):d}")
    print(f"gid: {(await self.symbols.getgid()):d}")
    print(f"pid: {await self.get_pid():d}")
    print(f"ppid: {(await self.symbols.getppid()):d}")
    print(f"progname: {await self.get_progname()}")
```

### get_progname

```
get_progname() -> str
```

get the program name from remote

Source code in `src/rpcclient/rpcclient/core/client.py`

```
async def get_progname(self) -> str:
    """get the program name from remote"""
    if self._cached_progname is None:
        # bugfix https://github.com/doronz88/rpc-project/issues/405
        # Default Linux libraries don't expose `getprogname()`, so instead we use the `__progname` global symbol.
        # Tested on both macOS and Ubuntu.
        self._cached_progname = await (await self.symbols["__progname"].getindex(0)).peek_str()

    return self._cached_progname
```

### progname

```
progname() -> str
```

get the program name from remote

Source code in `src/rpcclient/rpcclient/core/client.py`

```
async def progname(self) -> str:
    """get the program name from remote"""
    return await self.get_progname()
```

### get_uname

```
get_uname() -> Container
```

get the utsname struct from remote

Source code in `src/rpcclient/rpcclient/core/client.py`

```
@abc.abstractmethod
async def get_uname(self) -> Container:
    """get the utsname struct from remote"""
```

### uname

```
uname() -> Container
```

get the utsname struct from remote

Source code in `src/rpcclient/rpcclient/core/client.py`

```
async def uname(self) -> Container:
    """get the utsname struct from remote"""
    return await self.get_uname()
```

### dlopen

```
dlopen(filename: str, mode: int) -> SymbolT_co
```

Load a shared library on the remote host and return its handle.

Source code in `src/rpcclient/rpcclient/core/client.py`

```
async def dlopen(self, filename: str, mode: int) -> SymbolT_co:
    """Load a shared library on the remote host and return its handle."""
    return self.symbol((await self.rpc_call(MsgId.REQ_DLOPEN, filename=filename, mode=mode)).handle)
```

### dlclose

```
dlclose(lib: int) -> int
```

Close a previously opened remote library handle.

Source code in `src/rpcclient/rpcclient/core/client.py`

```
async def dlclose(self, lib: int) -> int:
    """Close a previously opened remote library handle."""
    return (await self.rpc_call(MsgId.REQ_DLCLOSE, handle=ctypes.c_uint64(lib).value)).res
```

### dlsym

```
dlsym(lib: int, symbol_name: str) -> int
```

Resolve a symbol name in a remote library handle and return its address.

Runs and pops any hooks in `self.pre_dlsym_hooks` first.

Source code in `src/rpcclient/rpcclient/core/client.py`

```
async def dlsym(self, lib: int, symbol_name: str) -> int:
    """Resolve a symbol name in a remote library handle and return its address.

    Runs and pops any hooks in `self.pre_dlsym_hooks` first.
    """
    return (await self.rpc_call(MsgId.REQ_DLSYM, handle=ctypes.c_uint64(lib).value, symbol_name=symbol_name)).ptr
```

### call

```
call(address: int, argv: Iterable[RemoteCallArg] = (), return_float64: bool = False, return_float32: bool = False, return_raw: bool = False, va_list_index: int | None = None) -> float | SymbolT_co | Any
```

call a remote function and retrieve its return value as a Symbol object

Source code in `src/rpcclient/rpcclient/core/client.py`

```
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

    ret = await self.rpc_call(MsgId.REQ_CALL, address=address, va_list_index=va_list_index, argv=args)
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
```

### peek

```
peek(address: int, size: int) -> bytes
```

peek data at the given address

Source code in `src/rpcclient/rpcclient/core/client.py`

```
@null_pointer_guard
async def peek(self, address: int, size: int) -> bytes:
    """peek data at the given address"""
    try:
        return (await self.rpc_call(MsgId.REQ_PEEK, address=address, size=size)).data
    except ServerResponseError as e:
        raise ArgumentError() from e
```

### poke

```
poke(address: int, data: bytes) -> Any
```

poke data at a given address

Source code in `src/rpcclient/rpcclient/core/client.py`

```
@null_pointer_guard
async def poke(self, address: int, data: bytes) -> Any:
    """poke data at a given address"""
    try:
        return await self.rpc_call(MsgId.REQ_POKE, address=address, data=data)
    except ServerResponseError as e:
        raise ArgumentError() from e
```

### get_dummy_block

```
get_dummy_block() -> SymbolT_co
```

Get an address for a stub block containing nothing

Source code in `src/rpcclient/rpcclient/core/client.py`

```
async def get_dummy_block(self) -> SymbolT_co:
    """Get an address for a stub block containing nothing"""
    block_size = block_literal.sizeof()
    desc_size = block_descriptor.sizeof()

    descriptor = await self.symbols.malloc(desc_size)
    await descriptor.poke(block_descriptor.build({"reserved": 0, "size": block_size}))

    block = await self.symbols.malloc(block_size)
    await block.poke(
        block_literal.build({
            "isa": await self.symbols._NSConcreteGlobalBlock.resolve(),
            "flags": BLOCK_IS_GLOBAL,
            "reserved": 0,
            "invoke": await self.symbols.getpid.resolve(),
            "descriptor": descriptor,
        }),
    )

    return block
```

### listdir

```
listdir(path: str | PurePath) -> list[ProtocolDirent]
```

get an address for a stub block containing nothing

Source code in `src/rpcclient/rpcclient/core/client.py`

```
async def listdir(self, path: str | PurePath) -> list[ProtocolDirent]:
    """get an address for a stub block containing nothing"""
    entries: list[ProtocolDirent] = []
    try:
        ret = await self.rpc_call(MsgId.REQ_LIST_DIR, path=str(path))
    except ServerResponseError:
        await self.raise_errno_exception(f"failed to listdir: {path}")

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
```

### spawn

```
spawn(argv: list[str] | None = None, envp: list[str] | None = None, stdin: StrOrIO = sys.stdin, stdout=sys.stdout, raw_tty=False, background=False) -> SpawnResult
```

spawn a new process and forward its stdin, stdout & stderr

Parameters:

| Name         | Type        | Description                                                                       | Default                            |
| ------------ | ----------- | --------------------------------------------------------------------------------- | ---------------------------------- |
| `argv`       | \`list[str] | None\`                                                                            | argv of the process to be executed |
| `envp`       | \`list[str] | None\`                                                                            | envp of the process to be executed |
| `stdin`      | `StrOrIO`   | either a file object to read from OR a string                                     | `stdin`                            |
| `stdout`     |             | a file object to write both stdout and stderr to. None if background is requested | `stdout`                           |
| `raw_tty`    |             | should enable raw tty mode                                                        | `False`                            |
| `background` |             | should execute process in background                                              | `False`                            |

Returns:

| Type          | Description                                             |
| ------------- | ------------------------------------------------------- |
| `SpawnResult` | a SpawnResult. error is None if background is requested |

Source code in `src/rpcclient/rpcclient/core/client.py`

```
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
            error = await self.enter_pty_mode(stdin, stdout)
        except Exception:
            # this is important to really catch every exception here, even exceptions not inheriting from Exception
            # so the controlling terminal will remain working with its previous settings
            if raw_tty:
                self._restore_terminal()
            raise

    return SpawnResult(error=error, pid=pid, stdout=stdout)
```

### symbol

```
symbol(symbol: int) -> SymbolT_co
```

Get a symbol object from a given address

Source code in `src/rpcclient/rpcclient/core/client.py`

```
@abc.abstractmethod
def symbol(self, symbol: int) -> SymbolT_co:
    """Get a symbol object from a given address"""
```

### get_last_error

```
get_last_error() -> str
```

get info about the last occurred error

Source code in `src/rpcclient/rpcclient/core/client.py`

```
async def get_last_error(self) -> str:
    """get info about the last occurred error"""
    if not (errno := await self.get_errno()):
        return ""
    err_str_ptr = await self.symbols.strerror(errno)
    err_str = await err_str_ptr.peek_str()
    return f"[{errno}] {err_str}"
```

### setenv

```
setenv(name: str, value: str) -> None
```

set process environment variable

Source code in `src/rpcclient/rpcclient/core/client.py`

```
async def setenv(self, name: str, value: str) -> None:
    """set process environment variable"""
    await (await self.symbols.setenv.resolve()).call(name, value)
```

### getenv

```
getenv(name: str) -> str | None
```

get process environment variable

Source code in `src/rpcclient/rpcclient/core/client.py`

```
async def getenv(self, name: str) -> str | None:
    """get process environment variable"""
    value = await self.symbols.getenv(name)
    if not isinstance(value, Symbol) or not value:
        return None
    return await value.peek_str()
```

### capture_fd

```
capture_fd(fd: int, sock_buf_size: int | None = None) -> CaptureFD[SymbolT_co]
```

Get a context manager, capturing output to `fd`. Read from it using the `read()` method

sock_buf_size is required for captures above 6KB, as any write above this value would block until a read is performed.

Parameters:

| Name            | Type  | Description   | Default                                                                      |
| --------------- | ----- | ------------- | ---------------------------------------------------------------------------- |
| `fd`            | `int` | FD to capture | *required*                                                                   |
| `sock_buf_size` | \`int | None\`        | Buffer size for the capture socket, if not specified, default value is used. |

Returns:

| Type                    | Description      |
| ----------------------- | ---------------- |
| `CaptureFD[SymbolT_co]` | CaptureFD object |

Source code in `src/rpcclient/rpcclient/core/client.py`

```
def capture_fd(self, fd: int, sock_buf_size: int | None = None) -> CaptureFD[SymbolT_co]:
    """
    Get a context manager, capturing output to `fd`. Read from it using the `read()` method

    sock_buf_size is required for captures above 6KB, as any write above this value would block until a read is performed.

    :param fd: FD to capture
    :param sock_buf_size: Buffer size for the capture socket, if not specified, default value is used.
    :return: CaptureFD object
    """
    return CaptureFD(self, fd, sock_buf_size)
```

## Filesystem

## rpcclient.core.subsystems.fs

### DirEntry

Bases: `ClientBound[ClientT_co]`

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
class DirEntry(ClientBound[ClientT_co]):
    def __init__(self, path, entry, client: ClientT_co) -> None:
        self._path = path
        self._entry = entry
        self._client = client
        self._stat = None

    @property
    def name(self) -> str:
        return self._entry.d_name

    @property
    def path(self) -> str:
        return posixpath.join(self._path, self.name)

    def inode(self):
        """Return inode of the entry; cached per entry."""
        return self._entry.d_ino

    async def is_dir(self, *, follow_symlinks=True) -> bool:
        """Return True if the entry is a directory; cached per entry."""
        return await self._test_mode(follow_symlinks, S_IFDIR)

    async def is_file(self, *, follow_symlinks: bool = True):
        """Return True if the entry is a file; cached per entry."""
        return await self._test_mode(follow_symlinks, S_IFREG)

    async def is_symlink(self) -> bool:
        """Return True if the entry is a symbolic link; cached per entry."""
        if self._entry.d_type != DT_UNKNOWN:
            return self._entry.d_type == DT_LNK
        else:
            return await self._test_mode(False, S_IFLNK)

    async def stat(self, *, follow_symlinks: bool = True):
        """Return stat_result object for the entry; cached per entry."""
        if not follow_symlinks:
            return await self._get_lstat()
        if self._stat is None:
            if await self.is_symlink():
                self._stat = await self._fetch_stat(True)
            else:
                self._stat = await self._get_lstat()
        return self._stat

    async def _test_mode(self, follow_symlinks, mode) -> bool:
        is_symlink = self._entry.d_type == DT_LNK
        need_stat = self._entry.d_type == DT_UNKNOWN or (follow_symlinks and is_symlink)
        if not need_stat:
            d_types = {S_IFLNK: DT_LNK, S_IFDIR: DT_DIR, S_IFREG: DT_REG}
            return self._entry.d_type == d_types[mode]
        else:
            st_mode = (await self.stat(follow_symlinks=follow_symlinks)).st_mode
            if not st_mode:
                await self._client.raise_errno_exception(f"failed to stat(): {self.path}")
            return (st_mode & S_IFMT) == mode

    @cached_async_method
    async def _get_lstat(self):
        return await self._fetch_stat(False)

    async def _fetch_stat(self, follow_symlinks):
        result = self._entry.stat
        if not follow_symlinks:
            result = self._entry.lstat

        if result.errno != 0:
            await self._client.set_errno(result.errno)
            await self._client.raise_errno_exception(f"failed to stat: {self._entry.d_name}")
        return result

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name!r}>"
```

#### inode

```
inode()
```

Return inode of the entry; cached per entry.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
def inode(self):
    """Return inode of the entry; cached per entry."""
    return self._entry.d_ino
```

#### is_dir

```
is_dir(*, follow_symlinks=True) -> bool
```

Return True if the entry is a directory; cached per entry.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def is_dir(self, *, follow_symlinks=True) -> bool:
    """Return True if the entry is a directory; cached per entry."""
    return await self._test_mode(follow_symlinks, S_IFDIR)
```

#### is_file

```
is_file(*, follow_symlinks: bool = True)
```

Return True if the entry is a file; cached per entry.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def is_file(self, *, follow_symlinks: bool = True):
    """Return True if the entry is a file; cached per entry."""
    return await self._test_mode(follow_symlinks, S_IFREG)
```

#### is_symlink

```
is_symlink() -> bool
```

Return True if the entry is a symbolic link; cached per entry.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def is_symlink(self) -> bool:
    """Return True if the entry is a symbolic link; cached per entry."""
    if self._entry.d_type != DT_UNKNOWN:
        return self._entry.d_type == DT_LNK
    else:
        return await self._test_mode(False, S_IFLNK)
```

#### stat

```
stat(*, follow_symlinks: bool = True)
```

Return stat_result object for the entry; cached per entry.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def stat(self, *, follow_symlinks: bool = True):
    """Return stat_result object for the entry; cached per entry."""
    if not follow_symlinks:
        return await self._get_lstat()
    if self._stat is None:
        if await self.is_symlink():
            self._stat = await self._fetch_stat(True)
        else:
            self._stat = await self._get_lstat()
    return self._stat
```

### File

Bases: `Allocated[ClientT_co]`

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
class File(Allocated[ClientT_co]):
    CHUNK_SIZE = 1024 * 64

    def __init__(self, client: ClientT_co, fd: int) -> None:
        """
        :param rpcclient.client.client.Client client:
        :param fd:
        """
        super().__init__()
        self._client = client
        self.fd: int = fd

    async def _deallocate(self) -> None:
        """Close the remote file descriptor."""
        fd = (await self._client.symbols.close(self.fd)).c_int32
        if fd < 0:
            await self._client.raise_errno_exception(f"failed to close fd: {fd}")

    async def seek(self, offset: int, whence: int) -> int:
        """Seek the remote file descriptor and return the resulting offset."""
        err = (await self._client.symbols.lseek(self.fd, offset, whence)).c_int64
        if err < 0:
            await self._client.raise_errno_exception(f"failed to lseek fd: {self.fd}")
        return err

    async def tell(self) -> int:
        return await self.seek(0, SEEK_CUR)

    async def _write(self, buf: bytes) -> int:
        """Write bytes to the remote file descriptor."""
        n = (await self._client.symbols.write(self.fd, buf, len(buf))).c_int64
        if n < 0:
            await self._client.raise_errno_exception(f"failed to write on fd: {self.fd}")
        return n

    async def write(self, buf: bytes) -> int:
        """Write the full buffer, retrying until all bytes are written. Return the number of bytes written."""
        total = len(buf)
        while buf:
            err = await self._write(buf)
            buf = buf[err:]
        return total

    async def _read(self, buf: "Symbol", size: int) -> bytes:
        """read file at remote"""
        err = (await self._client.symbols.read(self.fd, buf, size)).c_int64
        if err < 0:
            await self._client.raise_errno_exception(f"read() failed for fd: {self.fd}")
        return await buf.peek(err)

    async def read_using_chunk(self, chunk: "Symbol", chunk_size: int, size: int) -> bytes:
        buf = b""
        while size == -1 or len(buf) < size:
            read_chunk = await self._read(chunk, chunk_size)
            if not read_chunk:
                # EOF
                break
            buf += read_chunk
        return buf

    async def read(self, size: int = -1, chunk_size: int = CHUNK_SIZE, chunk: "Symbol | None" = None) -> bytes:
        """read file at remote"""
        if size != -1 and size < chunk_size:
            chunk_size = size

        if chunk:
            return await self.read_using_chunk(chunk, chunk_size, size)
        else:
            async with self._client.safe_malloc(chunk_size) as temp_chunk:
                return await self.read_using_chunk(temp_chunk, chunk_size, size)

    async def pread(self, length: int, offset: int) -> bytes:
        """call pread() at remote"""
        async with self._client.safe_malloc(length) as buf:
            err = (await self._client.symbols.pread(self.fd, buf, length, offset)).c_int64
            if err < 0:
                await self._client.raise_errno_exception(f"pread() failed for fd: {self.fd}")
            return await buf.peek(err)

    async def pwrite(self, buf: bytes, offset: int) -> None:
        """call pwrite() at remote"""
        err = (await self._client.symbols.pwrite(self.fd, buf, len(buf), offset)).c_int64
        if err < 0:
            await self._client.raise_errno_exception(f"pwrite() failed for fd: {self.fd}")

    async def fdatasync(self) -> None:
        err = (await self._client.symbols.fdatasync(self.fd)).c_int64
        if err < 0:
            await self._client.raise_errno_exception(f"fdatasync() failed for fd: {self.fd}")

    async def fsync(self) -> None:
        err = (await self._client.symbols.fsync(self.fd)).c_int64
        if err < 0:
            await self._client.raise_errno_exception(f"fsync() failed for fd: {self.fd}")

    async def flock(self, operation: int) -> None:
        """Apply or clear an advisory lock on the remote file descriptor."""
        err = (await self._client.symbols.flock(self.fd, operation)).c_int32
        if err < 0:
            await self._client.raise_errno_exception(f"flock() failed for fd: {self.fd}")

    async def dup(self) -> int:
        err = (await self._client.symbols.dup(self.fd)).c_int64
        if err < 0:
            await self._client.raise_errno_exception(f"dup() failed for fd: {self.fd}")
        return err

    def __repr__(self):
        return f"<{self.__class__.__name__} FD:{self.fd}>"

    async def parse(self, struct: "Construct[ParsedType, Any]") -> "ParsedType":
        return struct.parse(await self.read(struct.sizeof()))
```

#### seek

```
seek(offset: int, whence: int) -> int
```

Seek the remote file descriptor and return the resulting offset.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def seek(self, offset: int, whence: int) -> int:
    """Seek the remote file descriptor and return the resulting offset."""
    err = (await self._client.symbols.lseek(self.fd, offset, whence)).c_int64
    if err < 0:
        await self._client.raise_errno_exception(f"failed to lseek fd: {self.fd}")
    return err
```

#### write

```
write(buf: bytes) -> int
```

Write the full buffer, retrying until all bytes are written. Return the number of bytes written.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def write(self, buf: bytes) -> int:
    """Write the full buffer, retrying until all bytes are written. Return the number of bytes written."""
    total = len(buf)
    while buf:
        err = await self._write(buf)
        buf = buf[err:]
    return total
```

#### read

```
read(size: int = -1, chunk_size: int = CHUNK_SIZE, chunk: Symbol | None = None) -> bytes
```

read file at remote

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def read(self, size: int = -1, chunk_size: int = CHUNK_SIZE, chunk: "Symbol | None" = None) -> bytes:
    """read file at remote"""
    if size != -1 and size < chunk_size:
        chunk_size = size

    if chunk:
        return await self.read_using_chunk(chunk, chunk_size, size)
    else:
        async with self._client.safe_malloc(chunk_size) as temp_chunk:
            return await self.read_using_chunk(temp_chunk, chunk_size, size)
```

#### pread

```
pread(length: int, offset: int) -> bytes
```

call pread() at remote

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def pread(self, length: int, offset: int) -> bytes:
    """call pread() at remote"""
    async with self._client.safe_malloc(length) as buf:
        err = (await self._client.symbols.pread(self.fd, buf, length, offset)).c_int64
        if err < 0:
            await self._client.raise_errno_exception(f"pread() failed for fd: {self.fd}")
        return await buf.peek(err)
```

#### pwrite

```
pwrite(buf: bytes, offset: int) -> None
```

call pwrite() at remote

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def pwrite(self, buf: bytes, offset: int) -> None:
    """call pwrite() at remote"""
    err = (await self._client.symbols.pwrite(self.fd, buf, len(buf), offset)).c_int64
    if err < 0:
        await self._client.raise_errno_exception(f"pwrite() failed for fd: {self.fd}")
```

#### flock

```
flock(operation: int) -> None
```

Apply or clear an advisory lock on the remote file descriptor.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def flock(self, operation: int) -> None:
    """Apply or clear an advisory lock on the remote file descriptor."""
    err = (await self._client.symbols.flock(self.fd, operation)).c_int32
    if err < 0:
        await self._client.raise_errno_exception(f"flock() failed for fd: {self.fd}")
```

### RemotePath

Bases: `PurePosixPath`, `ClientBound[ClientT_co]`

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
class RemotePath(PurePosixPath, ClientBound[ClientT_co]):
    def __init__(self, *args: str | os.PathLike[str], client: ClientT_co) -> None:
        if sys.version_info < (3, 12):
            super().__init__()
        else:
            super().__init__(*args)  # solution from python3.12 since signature has changed
        self._path: str = posixpath.join(*args)
        self._client = client

    if sys.version_info < (3, 12):
        # this will not be needed once python3.11 is deprecated since it is now possible to subclass normally
        def __new__(cls, *args: str | os.PathLike[str], client: ClientT_co) -> Self:
            return super().__new__(cls, *args)

        def _make_child(self, args) -> Self:
            return self.with_segments(self, *args)

    def with_segments(self, *pathsegments: str | os.PathLike[str]) -> Self:
        return type(self)(*pathsegments, client=self._client)

    async def absolute(self) -> Self:
        if self.is_absolute():
            return self
        return self.with_segments(await self._client.fs.pwd(), self)

    async def chmod(self, mode: int) -> None:
        return await self._client.fs.chmod(self._path, mode)

    async def readlink(self) -> Self:
        return self.with_segments(await self._client.fs.readlink(self._path))

    async def exists(self) -> bool:
        try:
            await self.stat()
        except Exception:
            return False
        return True

    async def is_dir(self) -> bool:
        return bool((await self.stat()).st_mode & S_IFDIR)

    async def lstat(self) -> Any:
        return await self._client.fs.lstat(self._path)

    async def mkdir(self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        await self._client.fs.mkdir(self._path, mode, parents=parents, exist_ok=exist_ok)

    async def read_bytes(self) -> bytes:
        async with await self._open("r") as f:
            return await f.read()

    async def stat(self) -> Any:
        return await self._client.fs.stat(self._path)

    async def symlink_to(self, target: str | PurePath, target_is_directory: Literal[False] = False) -> None:
        await self._client.fs.symlink(target, self._path)

    async def write_bytes(self, data: Buffer) -> int:
        async with await self._open("w") as f:
            return await f.write(bytes(data))

    async def _open(self, mode: str, access: int = 0o777) -> File[ClientT_co]:
        return await self._client.fs.open(self._path, mode, access)

    async def iterdir(self) -> AsyncGenerator[Self]:
        for entry in await self._client.fs.listdir(self._path):
            yield self / entry

    async def touch(self, mode: int = 438, exist_ok: bool = True) -> None:
        try:
            return await self._client.fs.touch(self._path, mode, exist_ok)
        except RpcFileExistsError as e:
            raise FileExistsError() from e

    async def remove(self, recursive: bool = False, force: bool = False) -> None:
        """Remove the current path from the filesystem.

        :param recursive:
        :param force:
        """
        if await self.exists():
            await self._client.fs.remove(self._path, recursive=recursive, force=force)
```

#### remove

```
remove(recursive: bool = False, force: bool = False) -> None
```

Remove the current path from the filesystem.

Parameters:

| Name        | Type   | Description | Default |
| ----------- | ------ | ----------- | ------- |
| `recursive` | `bool` |             | `False` |
| `force`     | `bool` |             | `False` |

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def remove(self, recursive: bool = False, force: bool = False) -> None:
    """Remove the current path from the filesystem.

    :param recursive:
    :param force:
    """
    if await self.exists():
        await self._client.fs.remove(self._path, recursive=recursive, force=force)
```

### RemoteTemporaryDir

Bases: `RemotePath[ClientT_co]`

Temporary directory on the remote device

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
class RemoteTemporaryDir(RemotePath[ClientT_co]):
    """Temporary directory on the remote device"""

    _deleted: bool = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.deallocate()

    async def deallocate(self) -> None:
        if not self._deleted:
            await self.remove(recursive=True, force=True)
            self._deleted = True
```

### Fs

Bases: `ClientBound[ClientT_co]`, `ABC`

filesystem utils

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
class Fs(ClientBound[ClientT_co], abc.ABC):
    """filesystem utils"""

    def __init__(self, client: ClientT_co) -> None:
        self._client = client

    async def _cp_dir(
        self,
        source: Path | RemotePath[ClientT_co],
        dest: Path | RemotePath[ClientT_co],
        force: bool,
    ) -> None:
        if not await _do_path_op(dest.exists):
            await _do_path_op(dest.mkdir, (await _do_path_op(source.lstat)).st_mode)

        if isinstance(source, Path):

            async def _make_async_gen() -> AsyncGenerator[Path]:
                for file in source.iterdir():
                    yield file

            files = _make_async_gen()
        else:
            files = source.iterdir()

        async for src_file in files:
            dest_file = dest / src_file.name

            src_lstat = await _do_path_op(src_file.lstat)
            if stat.S_ISDIR(src_lstat.st_mode):
                await self._cp_dir(src_file, dest_file, force)
            elif stat.S_ISLNK(src_lstat.st_mode):
                symlink_full = await _do_path_op(src_file.readlink)
                await _do_path_op(dest_file.symlink_to, symlink_full)
            elif await _do_path_op(dest_file.exists) and not force:
                pass
            else:
                await _do_path_op(dest_file.write_bytes, await _do_path_op(src_file.read_bytes))

    async def cp(
        self,
        sources: Collection[Path] | Collection[RemotePath[ClientT_co]],
        dest: Path | RemotePath[ClientT_co],
        recursive: bool,
        force: bool,
    ) -> None:
        dest_exists = await _do_path_op(dest.exists)
        is_dest_dir = dest_exists and await _do_path_op(dest.is_dir)

        if (not dest_exists or not is_dest_dir) and (len(sources) > 1):
            raise ArgumentError(f"target {dest} is not a directory")

        if recursive and not dest_exists:
            try:
                await _do_path_op(dest.mkdir, 0o777)
            except Exception:
                if not await _do_path_op(dest.exists):
                    raise

        for source in sources:
            if not await _do_path_op(source.exists):
                raise ArgumentError(f"cannot stat {source}: No such file or directory")

            if await _do_path_op(source.is_dir):
                if not recursive:
                    logger.info(f"omitting directory {source}")
                else:
                    cur_dest = dest / source.name
                    source_mode = (await _do_path_op(source.stat)).st_mode
                    if not await _do_path_op(cur_dest.exists):
                        await _do_path_op(cur_dest.mkdir, source_mode)
                    await self._cp_dir(source, cur_dest, force)
            else:  # source is a file
                cur_dest = dest
                if await _do_path_op(dest.exists) and await _do_path_op(dest.is_dir):
                    cur_dest = dest / source.name
                if not await _do_path_op(cur_dest.exists) or force:
                    await _do_path_op(cur_dest.write_bytes, await _do_path_op(source.read_bytes))

    async def is_file(self, path: str | PurePath) -> bool:
        """Return True if the entry is a file"""
        return bool((await self.stat(path)).st_mode & S_IFREG)

    async def _chown(self, path: str | PurePath, uid: int, gid: int) -> None:
        """Change owner and group for a remote path."""
        if (await self._client.symbols.chown(path, uid, gid)).c_int32 < 0:
            await self._client.raise_errno_exception(f"failed to chown: {path}")

    async def chown(self, path: str | PurePath, uid: int, gid: int, recursive: bool = False) -> None:
        """Change owner and group for a path, optionally recursively."""
        if not recursive:
            await self._chown(path, uid, gid)
            return

        async for file in self.find(path, topdown=False):
            await self._chown(file, uid, gid)

    async def _chmod(self, path: str | PurePath, mode: int) -> None:
        """Change mode bits for a remote path."""
        if (await self._client.symbols.chmod(path, mode)).c_int32 < 0:
            await self._client.raise_errno_exception(f"failed to chmod: {path}")

    async def chmod(self, path: str | PurePath, mode: int, recursive: bool = False) -> None:
        """Change mode bits for a path, optionally recursively."""
        if not recursive:
            await self._chmod(path, mode)
            return

        async for file in self.find(path, topdown=False):
            await self._chmod(file, mode)

    async def _remove(self, path: str | PurePath, force=False) -> None:
        """Remove a file on the remote filesystem."""
        if (await self._client.symbols.remove(path)).c_int32 < 0 and not force:
            await self._client.raise_errno_exception(f"failed to remove: {path}")

    async def remove(self, path: str | PurePath, recursive: bool = False, force: bool = False) -> None:
        """Remove a file or directory tree on the remote filesystem."""
        if not recursive or await self.is_file(path):
            await self._remove(path, force=force)
            return

        async for filename in self.find(path, topdown=False):
            await self._remove(filename, force=force)

    async def rename(self, old: str | PurePath, new: str | PurePath) -> None:
        """Rename or move a path on the remote filesystem."""
        if (await self._client.symbols.rename(old, new)).c_int32 < 0:
            await self._client.raise_errno_exception(f"failed to rename: {old} -> {new}")

    async def _mkdir(self, path: str | PurePath, mode: int = 0o777) -> None:
        """Create a directory on the remote filesystem."""
        if (await self._client.symbols.mkdir(path, mode)).c_int64 < 0:
            await self._client.raise_errno_exception(f"failed to mkdir: {path}")

        # os may not always respect the permission given by the mode argument to mkdir
        await self.chmod(path, mode)

    async def mkdir(
        self,
        path: str | PurePath,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        """Create a directory, optionally creating parent directories."""
        if not parents:
            try:
                await self._mkdir(path, mode=mode)
            except RpcFileExistsError:
                if not exist_ok:
                    raise
            return

        dir_path = PurePosixPath(await self.pwd())
        for part in PurePosixPath(path).parts:
            dir_path = dir_path / part
            with contextlib.suppress(RpcIsADirectoryError, RpcFileExistsError):
                await self._mkdir(dir_path, mode=mode)

    async def chdir(self, path: str | PurePath) -> None:
        """Change the remote process working directory."""
        if (await self._client.symbols.chdir(path)).c_int64 < 0:
            await self._client.raise_errno_exception(f"failed to chdir: {path}")

    async def readlink(self, path: str | PurePath, absolute: bool = True) -> str:
        """Read the symlink target on the remote filesystem."""
        async with self._client.safe_calloc(MAXPATHLEN) as buf:
            if (await self._client.symbols.readlink(path, buf, MAXPATHLEN)).c_int64 < 0:
                await self._client.raise_errno_exception(f"readlink failed for: {path}")
            if absolute:
                return str(Path(path).parent / await buf.peek_str())
            return await buf.peek_str()

    async def realpath(self, path: str | PurePath) -> str:
        """Resolve a path on the remote filesystem to an absolute path."""
        async with self._client.safe_malloc(MAXPATHLEN) as buf:
            if await self._client.symbols.realpath(path, buf) == 0:
                await self._client.raise_errno_exception(f"realpath failed for: {path}")
            return await buf.peek_str()

    async def is_symlink(self, path: str | PurePath) -> bool:
        try:
            await self.readlink(path)
        except BadReturnValueError:
            return False
        return True

    async def open(self, file: str | PurePath, mode: str, access: int = 0o777) -> File[ClientT_co]:
        """
        call open(file, mode, access) at remote and get a context manager
        file object
        :param file: filename to be opened
        :param mode: one of:
            'r' - read only
            'r+' - read and write. exception if file doesn't exist
            'rw' - read and write. create if it doesn't exist. also truncate.
            'w' - write only. create if it doesn't exist. also truncate.
            'w+' - read and write. create if it doesn't exist.
        :param access: access mode as octal value
        :return: a context manager file object
        """
        available_modes = {
            "r": O_RDONLY,
            "r+": O_RDWR,
            "rw": O_RDWR | O_CREAT | O_TRUNC,
            "w": O_WRONLY | O_CREAT | O_TRUNC,
            "w+": O_RDWR | O_CREAT,
        }
        mode_int = available_modes.get(mode)
        if mode_int is None:
            raise ArgumentError(f"mode can be only one of: {available_modes.keys()}")

        fd = (await self._client.symbols.open(file, mode_int, access, va_list_index=2)).c_int32
        if fd < 0:
            await self._client.raise_errno_exception(f"failed to open: {file}")

        return File(self._client, fd)

    async def write_file(self, file: str | PurePath, buf: bytes, access: int = 0o777) -> None:
        async with await self.open(file, "w", access=access) as f:
            await f.write(buf)

    async def read_file(self, file: str | PurePath) -> bytes:
        async with await self.open(file, "r") as f:
            return await f.read()

    def remote_path(self, path: str | PurePath) -> RemotePath[ClientT_co]:
        return RemotePath(path, client=self._client)

    async def pull(
        self,
        remotes: list[str | PurePath] | str | PurePath,
        local: str | PurePath,
        recursive: bool = False,
        force: bool = False,
    ):
        """pull complete directory tree"""
        if not isinstance(remotes, list):
            remotes = [posixpath.expanduser(remotes)]
        remotes_str = [posixpath.expanduser(remote) for remote in remotes]
        await self.cp([self.remote_path(remote) for remote in remotes_str], Path(str(local)), recursive, force)

    async def push(
        self,
        local_files: list[str | PurePath] | str | PurePath,
        remote: str | PurePath,
        recursive: bool = False,
        force: bool = False,
    ):
        """push complete directory tree"""
        if not isinstance(local_files, list):
            local_files = [posixpath.expanduser(local_files)]
        locals_str = [posixpath.expanduser(local) for local in local_files]
        await self.cp([Path(str(local)) for local in locals_str], self.remote_path(remote), recursive, force)

    async def touch(self, file: str | PurePath, mode: int = 0o666, exist_ok: bool = True) -> None:
        """simulate unix touch command for given file"""
        if not exist_ok:
            try:
                await self.stat(file)
                raise RpcFileExistsError()
            except RpcFileNotFoundError:
                pass
        async with await self.open(file, "w+", mode):
            pass

    async def symlink(self, src: str | PurePath, dst: str | PurePath) -> int:
        """Create a symbolic link on the remote filesystem."""
        err = (await self._client.symbols.symlink(src, dst)).c_int64
        if err < 0:
            await self._client.raise_errno_exception(f"symlink failed to create link: {dst}->{src}")
        return err

    async def link(self, src: str | PurePath, dst: str | PurePath) -> int:
        """Create a hard link on the remote filesystem."""
        err = (await self._client.symbols.link(src, dst)).c_int64
        if err < 0:
            await self._client.raise_errno_exception(f"link failed to create link: {dst}->{src}")
        return err

    async def pwd(self) -> str:
        """calls getcwd(buf, size_t) and prints current path.
        with the special values NULL, 0 the buffer is allocated dynamically"""
        chunk = await self._client.symbols.getcwd(0, 0)
        if chunk == 0:
            await self._client.raise_errno_exception("getcwd() failed")
        try:
            return await chunk.peek_str()
        finally:
            await self._client.symbols.free(chunk)

    async def listdir(self, path: str | PurePath = ".") -> list[str]:
        """get directory listing for a given dirname"""
        return [e.name for e in await self.scandir(path)]

    async def scandir(self, path: str | PurePath = ".") -> list[DirEntry[ClientT_co]]:
        """get directory listing for a given dirname"""
        result = []
        for entry in (await self._client.listdir(path))[2:]:
            result.append(DirEntry(path, entry, self._client))
        return result

    @abc.abstractmethod
    async def stat(self, path: str | PurePath) -> Any:
        """Return stat info for a remote path (platform-specific implementation)."""

    @abc.abstractmethod
    async def lstat(self, path: str | PurePath) -> Any:
        """Return lstat info for a remote path (platform-specific implementation)."""

    async def accessible(self, path: str | PurePath, mode: int = R_OK) -> bool:
        """check if a given path can be accessed."""
        err = await self._client.symbols.access(path, mode)
        return err == 0

    async def chflags(self, path: str | PurePath, flags: int = 0) -> None:
        """set file flags"""
        err = await self._client.symbols.chflags(path, flags)
        if err < 0:
            await self._client.raise_errno_exception(f"failed to chflags on: {path}")

    async def find(self, top: str | PurePath, topdown: bool = True) -> AsyncGenerator[str]:
        """traverse a file tree top to down"""
        top = str(top)
        if topdown:
            if await self.accessible(top):
                yield top
            else:
                raise RpcFileNotFoundError(f"cannot access: {top}")

        async for root, dirs, files in self.walk(top, topdown=topdown):
            for name in files:
                yield os.path.join(root, name)
            for name in dirs:
                yield os.path.join(root, name)

        if not topdown:
            if await self.accessible(top):
                yield top
            else:
                raise RpcFileNotFoundError(f"cannot access: {top}")

    async def walk(
        self,
        top: str | PurePath,
        topdown: bool = True,
        onerror: Callable[[Exception], object] | None = None,
    ) -> AsyncGenerator[tuple[str, list[str], list[str]]]:
        """provides the same results as os.walk(top)"""
        top = str(top)
        dirs = []
        files = []
        try:
            for entry in await self.scandir(top):
                try:
                    if await entry.is_dir():
                        dirs.append(entry.name)
                    else:
                        files.append(entry.name)
                except Exception as e:
                    if not onerror:
                        raise
                    onerror(e)
        except Exception as e:
            if not onerror:
                raise
            onerror(e)

        if topdown:
            yield top, dirs, files

        for d in dirs:
            async for item in self.walk(posixpath.join(top, d), topdown=topdown, onerror=onerror):
                yield item

        if not topdown:
            yield top, dirs, files

    @asynccontextmanager
    async def remote_file(self, remote: str | PurePath) -> AsyncGenerator[Path]:
        with tempfile.TemporaryDirectory() as local_dir:
            local = Path(local_dir) / PurePosixPath(remote).name
            if await self.accessible(remote):
                await self.pull(remote, local.absolute())
            try:
                yield local.absolute()
            finally:
                await self.push(local, remote, force=True)

    async def remote_temp_dir(
        self, directory: str | PurePath = "/tmp", mode: int = 0o700
    ) -> RemoteTemporaryDir[ClientT_co]:
        """Generate a random temp directory name and create it in the given directory (default '/tmp').

        :param directory: Directory to create the temp directory inside (default '/tmp').
        :param mode: Mode to create the temp directory with (default 0o700).
        """
        remote_dir = self.remote_path(directory)
        if not await remote_dir.exists():
            raise RpcFileNotFoundError(f"remote dir {remote_dir} does not exist")

        while True:
            temp_dir = remote_dir / ("tmpdir_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789_", k=8)))
            try:
                await temp_dir.mkdir(mode=mode)
            except RpcFileExistsError:
                continue
            break

        return RemoteTemporaryDir(temp_dir, client=self._client)
```

#### is_file

```
is_file(path: str | PurePath) -> bool
```

Return True if the entry is a file

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def is_file(self, path: str | PurePath) -> bool:
    """Return True if the entry is a file"""
    return bool((await self.stat(path)).st_mode & S_IFREG)
```

#### chown

```
chown(path: str | PurePath, uid: int, gid: int, recursive: bool = False) -> None
```

Change owner and group for a path, optionally recursively.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def chown(self, path: str | PurePath, uid: int, gid: int, recursive: bool = False) -> None:
    """Change owner and group for a path, optionally recursively."""
    if not recursive:
        await self._chown(path, uid, gid)
        return

    async for file in self.find(path, topdown=False):
        await self._chown(file, uid, gid)
```

#### chmod

```
chmod(path: str | PurePath, mode: int, recursive: bool = False) -> None
```

Change mode bits for a path, optionally recursively.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def chmod(self, path: str | PurePath, mode: int, recursive: bool = False) -> None:
    """Change mode bits for a path, optionally recursively."""
    if not recursive:
        await self._chmod(path, mode)
        return

    async for file in self.find(path, topdown=False):
        await self._chmod(file, mode)
```

#### remove

```
remove(path: str | PurePath, recursive: bool = False, force: bool = False) -> None
```

Remove a file or directory tree on the remote filesystem.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def remove(self, path: str | PurePath, recursive: bool = False, force: bool = False) -> None:
    """Remove a file or directory tree on the remote filesystem."""
    if not recursive or await self.is_file(path):
        await self._remove(path, force=force)
        return

    async for filename in self.find(path, topdown=False):
        await self._remove(filename, force=force)
```

#### rename

```
rename(old: str | PurePath, new: str | PurePath) -> None
```

Rename or move a path on the remote filesystem.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def rename(self, old: str | PurePath, new: str | PurePath) -> None:
    """Rename or move a path on the remote filesystem."""
    if (await self._client.symbols.rename(old, new)).c_int32 < 0:
        await self._client.raise_errno_exception(f"failed to rename: {old} -> {new}")
```

#### mkdir

```
mkdir(path: str | PurePath, mode: int = 511, parents: bool = False, exist_ok: bool = False) -> None
```

Create a directory, optionally creating parent directories.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def mkdir(
    self,
    path: str | PurePath,
    mode: int = 0o777,
    parents: bool = False,
    exist_ok: bool = False,
) -> None:
    """Create a directory, optionally creating parent directories."""
    if not parents:
        try:
            await self._mkdir(path, mode=mode)
        except RpcFileExistsError:
            if not exist_ok:
                raise
        return

    dir_path = PurePosixPath(await self.pwd())
    for part in PurePosixPath(path).parts:
        dir_path = dir_path / part
        with contextlib.suppress(RpcIsADirectoryError, RpcFileExistsError):
            await self._mkdir(dir_path, mode=mode)
```

#### chdir

```
chdir(path: str | PurePath) -> None
```

Change the remote process working directory.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def chdir(self, path: str | PurePath) -> None:
    """Change the remote process working directory."""
    if (await self._client.symbols.chdir(path)).c_int64 < 0:
        await self._client.raise_errno_exception(f"failed to chdir: {path}")
```

#### readlink

```
readlink(path: str | PurePath, absolute: bool = True) -> str
```

Read the symlink target on the remote filesystem.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def readlink(self, path: str | PurePath, absolute: bool = True) -> str:
    """Read the symlink target on the remote filesystem."""
    async with self._client.safe_calloc(MAXPATHLEN) as buf:
        if (await self._client.symbols.readlink(path, buf, MAXPATHLEN)).c_int64 < 0:
            await self._client.raise_errno_exception(f"readlink failed for: {path}")
        if absolute:
            return str(Path(path).parent / await buf.peek_str())
        return await buf.peek_str()
```

#### realpath

```
realpath(path: str | PurePath) -> str
```

Resolve a path on the remote filesystem to an absolute path.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def realpath(self, path: str | PurePath) -> str:
    """Resolve a path on the remote filesystem to an absolute path."""
    async with self._client.safe_malloc(MAXPATHLEN) as buf:
        if await self._client.symbols.realpath(path, buf) == 0:
            await self._client.raise_errno_exception(f"realpath failed for: {path}")
        return await buf.peek_str()
```

#### open

```
open(file: str | PurePath, mode: str, access: int = 511) -> File[ClientT_co]
```

call open(file, mode, access) at remote and get a context manager file object

Parameters:

| Name     | Type  | Description                                                                                                                                                                                                                                                      | Default               |
| -------- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| `file`   | \`str | PurePath\`                                                                                                                                                                                                                                                       | filename to be opened |
| `mode`   | `str` | one of: 'r' - read only 'r+' - read and write. exception if file doesn't exist 'rw' - read and write. create if it doesn't exist. also truncate. 'w' - write only. create if it doesn't exist. also truncate. 'w+' - read and write. create if it doesn't exist. | *required*            |
| `access` | `int` | access mode as octal value                                                                                                                                                                                                                                       | `511`                 |

Returns:

| Type               | Description                   |
| ------------------ | ----------------------------- |
| `File[ClientT_co]` | a context manager file object |

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def open(self, file: str | PurePath, mode: str, access: int = 0o777) -> File[ClientT_co]:
    """
    call open(file, mode, access) at remote and get a context manager
    file object
    :param file: filename to be opened
    :param mode: one of:
        'r' - read only
        'r+' - read and write. exception if file doesn't exist
        'rw' - read and write. create if it doesn't exist. also truncate.
        'w' - write only. create if it doesn't exist. also truncate.
        'w+' - read and write. create if it doesn't exist.
    :param access: access mode as octal value
    :return: a context manager file object
    """
    available_modes = {
        "r": O_RDONLY,
        "r+": O_RDWR,
        "rw": O_RDWR | O_CREAT | O_TRUNC,
        "w": O_WRONLY | O_CREAT | O_TRUNC,
        "w+": O_RDWR | O_CREAT,
    }
    mode_int = available_modes.get(mode)
    if mode_int is None:
        raise ArgumentError(f"mode can be only one of: {available_modes.keys()}")

    fd = (await self._client.symbols.open(file, mode_int, access, va_list_index=2)).c_int32
    if fd < 0:
        await self._client.raise_errno_exception(f"failed to open: {file}")

    return File(self._client, fd)
```

#### pull

```
pull(remotes: list[str | PurePath] | str | PurePath, local: str | PurePath, recursive: bool = False, force: bool = False)
```

pull complete directory tree

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def pull(
    self,
    remotes: list[str | PurePath] | str | PurePath,
    local: str | PurePath,
    recursive: bool = False,
    force: bool = False,
):
    """pull complete directory tree"""
    if not isinstance(remotes, list):
        remotes = [posixpath.expanduser(remotes)]
    remotes_str = [posixpath.expanduser(remote) for remote in remotes]
    await self.cp([self.remote_path(remote) for remote in remotes_str], Path(str(local)), recursive, force)
```

#### push

```
push(local_files: list[str | PurePath] | str | PurePath, remote: str | PurePath, recursive: bool = False, force: bool = False)
```

push complete directory tree

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def push(
    self,
    local_files: list[str | PurePath] | str | PurePath,
    remote: str | PurePath,
    recursive: bool = False,
    force: bool = False,
):
    """push complete directory tree"""
    if not isinstance(local_files, list):
        local_files = [posixpath.expanduser(local_files)]
    locals_str = [posixpath.expanduser(local) for local in local_files]
    await self.cp([Path(str(local)) for local in locals_str], self.remote_path(remote), recursive, force)
```

#### touch

```
touch(file: str | PurePath, mode: int = 438, exist_ok: bool = True) -> None
```

simulate unix touch command for given file

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def touch(self, file: str | PurePath, mode: int = 0o666, exist_ok: bool = True) -> None:
    """simulate unix touch command for given file"""
    if not exist_ok:
        try:
            await self.stat(file)
            raise RpcFileExistsError()
        except RpcFileNotFoundError:
            pass
    async with await self.open(file, "w+", mode):
        pass
```

#### symlink

```
symlink(src: str | PurePath, dst: str | PurePath) -> int
```

Create a symbolic link on the remote filesystem.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def symlink(self, src: str | PurePath, dst: str | PurePath) -> int:
    """Create a symbolic link on the remote filesystem."""
    err = (await self._client.symbols.symlink(src, dst)).c_int64
    if err < 0:
        await self._client.raise_errno_exception(f"symlink failed to create link: {dst}->{src}")
    return err
```

#### link

```
link(src: str | PurePath, dst: str | PurePath) -> int
```

Create a hard link on the remote filesystem.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def link(self, src: str | PurePath, dst: str | PurePath) -> int:
    """Create a hard link on the remote filesystem."""
    err = (await self._client.symbols.link(src, dst)).c_int64
    if err < 0:
        await self._client.raise_errno_exception(f"link failed to create link: {dst}->{src}")
    return err
```

#### pwd

```
pwd() -> str
```

calls getcwd(buf, size_t) and prints current path. with the special values NULL, 0 the buffer is allocated dynamically

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def pwd(self) -> str:
    """calls getcwd(buf, size_t) and prints current path.
    with the special values NULL, 0 the buffer is allocated dynamically"""
    chunk = await self._client.symbols.getcwd(0, 0)
    if chunk == 0:
        await self._client.raise_errno_exception("getcwd() failed")
    try:
        return await chunk.peek_str()
    finally:
        await self._client.symbols.free(chunk)
```

#### listdir

```
listdir(path: str | PurePath = '.') -> list[str]
```

get directory listing for a given dirname

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def listdir(self, path: str | PurePath = ".") -> list[str]:
    """get directory listing for a given dirname"""
    return [e.name for e in await self.scandir(path)]
```

#### scandir

```
scandir(path: str | PurePath = '.') -> list[DirEntry[ClientT_co]]
```

get directory listing for a given dirname

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def scandir(self, path: str | PurePath = ".") -> list[DirEntry[ClientT_co]]:
    """get directory listing for a given dirname"""
    result = []
    for entry in (await self._client.listdir(path))[2:]:
        result.append(DirEntry(path, entry, self._client))
    return result
```

#### stat

```
stat(path: str | PurePath) -> Any
```

Return stat info for a remote path (platform-specific implementation).

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
@abc.abstractmethod
async def stat(self, path: str | PurePath) -> Any:
    """Return stat info for a remote path (platform-specific implementation)."""
```

#### lstat

```
lstat(path: str | PurePath) -> Any
```

Return lstat info for a remote path (platform-specific implementation).

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
@abc.abstractmethod
async def lstat(self, path: str | PurePath) -> Any:
    """Return lstat info for a remote path (platform-specific implementation)."""
```

#### accessible

```
accessible(path: str | PurePath, mode: int = R_OK) -> bool
```

check if a given path can be accessed.

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def accessible(self, path: str | PurePath, mode: int = R_OK) -> bool:
    """check if a given path can be accessed."""
    err = await self._client.symbols.access(path, mode)
    return err == 0
```

#### chflags

```
chflags(path: str | PurePath, flags: int = 0) -> None
```

set file flags

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def chflags(self, path: str | PurePath, flags: int = 0) -> None:
    """set file flags"""
    err = await self._client.symbols.chflags(path, flags)
    if err < 0:
        await self._client.raise_errno_exception(f"failed to chflags on: {path}")
```

#### find

```
find(top: str | PurePath, topdown: bool = True) -> AsyncGenerator[str]
```

traverse a file tree top to down

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def find(self, top: str | PurePath, topdown: bool = True) -> AsyncGenerator[str]:
    """traverse a file tree top to down"""
    top = str(top)
    if topdown:
        if await self.accessible(top):
            yield top
        else:
            raise RpcFileNotFoundError(f"cannot access: {top}")

    async for root, dirs, files in self.walk(top, topdown=topdown):
        for name in files:
            yield os.path.join(root, name)
        for name in dirs:
            yield os.path.join(root, name)

    if not topdown:
        if await self.accessible(top):
            yield top
        else:
            raise RpcFileNotFoundError(f"cannot access: {top}")
```

#### walk

```
walk(top: str | PurePath, topdown: bool = True, onerror: Callable[[Exception], object] | None = None) -> AsyncGenerator[tuple[str, list[str], list[str]]]
```

provides the same results as os.walk(top)

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def walk(
    self,
    top: str | PurePath,
    topdown: bool = True,
    onerror: Callable[[Exception], object] | None = None,
) -> AsyncGenerator[tuple[str, list[str], list[str]]]:
    """provides the same results as os.walk(top)"""
    top = str(top)
    dirs = []
    files = []
    try:
        for entry in await self.scandir(top):
            try:
                if await entry.is_dir():
                    dirs.append(entry.name)
                else:
                    files.append(entry.name)
            except Exception as e:
                if not onerror:
                    raise
                onerror(e)
    except Exception as e:
        if not onerror:
            raise
        onerror(e)

    if topdown:
        yield top, dirs, files

    for d in dirs:
        async for item in self.walk(posixpath.join(top, d), topdown=topdown, onerror=onerror):
            yield item

    if not topdown:
        yield top, dirs, files
```

#### remote_temp_dir

```
remote_temp_dir(directory: str | PurePath = '/tmp', mode: int = 448) -> RemoteTemporaryDir[ClientT_co]
```

Generate a random temp directory name and create it in the given directory (default '/tmp').

Parameters:

| Name        | Type  | Description                                             | Default                                                         |
| ----------- | ----- | ------------------------------------------------------- | --------------------------------------------------------------- |
| `directory` | \`str | PurePath\`                                              | Directory to create the temp directory inside (default '/tmp'). |
| `mode`      | `int` | Mode to create the temp directory with (default 0o700). | `448`                                                           |

Source code in `src/rpcclient/rpcclient/core/subsystems/fs.py`

```
async def remote_temp_dir(
    self, directory: str | PurePath = "/tmp", mode: int = 0o700
) -> RemoteTemporaryDir[ClientT_co]:
    """Generate a random temp directory name and create it in the given directory (default '/tmp').

    :param directory: Directory to create the temp directory inside (default '/tmp').
    :param mode: Mode to create the temp directory with (default 0o700).
    """
    remote_dir = self.remote_path(directory)
    if not await remote_dir.exists():
        raise RpcFileNotFoundError(f"remote dir {remote_dir} does not exist")

    while True:
        temp_dir = remote_dir / ("tmpdir_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789_", k=8)))
        try:
            await temp_dir.mkdir(mode=mode)
        except RpcFileExistsError:
            continue
        break

    return RemoteTemporaryDir(temp_dir, client=self._client)
```

## Network

## rpcclient.core.subsystems.network

### Socket

Bases: `Allocated[ClientT_co]`

Source code in `src/rpcclient/rpcclient/core/subsystems/network.py`

```
class Socket(Allocated[ClientT_co]):
    CHUNK_SIZE = 1024

    def __init__(self, client: ClientT_co, fd: int) -> None:
        """
        :param rpcclient.client.client.Client client:
        :param fd:
        """
        super().__init__()
        self._client = client
        self.fd: int = fd
        self._blocking: bool | None = None
        self._timeout = None

    async def _deallocate(self) -> None:
        """Close the remote socket file descriptor."""
        fd = (await self._client.symbols.close(self.fd)).c_int32
        if fd < 0:
            raise BadReturnValueError(f"failed to close fd: {fd}")

    async def send(self, buf: bytes | Symbol, size: int | None = None, flags: int = 0) -> int:
        """
        Send bytes from buf on the remote socket fd.

        :param buf: buffer to send
        :param size: If None, use len(buf)
        :param flags: flags for send() syscall. MSG_NOSIGNAL will always be added
        :return: how many bytes were sent
        """
        if size is None:
            if isinstance(buf, Symbol):
                raise ValueError("cannot calculate size argument for Symbol objects")
            size = len(buf)
        n = (await self._client.symbols.send(self.fd, buf, size, MSG_NOSIGNAL | flags)).c_int64
        if n < 0:
            if await self._client.get_errno() == EPIPE:
                await self.deallocate()
            await self._client.raise_errno_exception(f"failed to send on fd: {self.fd}")
        return n

    async def sendall(self, buf: bytes, flags: int = 0) -> None:
        """Send the entire buffer, retrying until all bytes are written."""
        size = len(buf)
        offset = 0
        async with self._client.safe_malloc(size) as block:
            await block.poke(buf)
            while offset < size:
                sent = await self.send(block + offset, size - offset, flags=flags)
                offset += sent

    async def _recv(self, chunk: Symbol, size: int, flags: int = 0) -> bytes:
        err = (await self._client.symbols.recv(self.fd, chunk, size, MSG_NOSIGNAL | flags)).c_int64
        if err < 0:
            await self._client.raise_errno_exception(f"recv() failed for fd: {self.fd}")
        elif err == 0:
            await self._client.raise_errno_exception(f"recv() failed for fd: {self.fd} (peer closed)")
        return await chunk.peek(err)

    async def recv(self, size: int = CHUNK_SIZE, flags: int = 0) -> bytes:
        """
        Receive up to size bytes from the remote socket fd.

        :param size: chunk size
        :param flags: flags for recv() syscall. MSG_NOSIGNAL will always be added
        :return: received bytes
        """
        async with self._client.safe_malloc(size) as chunk:
            return await self._recv(chunk, size, flags=flags)

    async def recvall(self, size: int, flags: int = 0) -> bytes:
        """recv at remote until all buffer is received"""
        buf = b""
        async with self._client.safe_malloc(size) as chunk:
            while len(buf) < size:
                buf += await self._recv(chunk, size - len(buf), flags=flags)
        return buf

    async def setsockopt(self, level: int, option_name: int, option_value: bytes):
        if await self._client.symbols.setsockopt(self.fd, level, option_name, option_value, len(option_value)) != 0:
            await self._client.raise_errno_exception(f"setsockopt() failed: {await self._client.get_last_error()}")

    async def setbufsize(self, size: int) -> None:
        await self.setsockopt(SOL_SOCKET, SO_SNDBUF, uint32_t.build(size))
        await self.setsockopt(SOL_SOCKET, SO_RCVBUF, uint32_t.build(size))

    async def settimeout(self, seconds: int) -> None:
        self._timeout = seconds
        await self.setsockopt(SOL_SOCKET, SO_RCVTIMEO, timeval.build({"tv_sec": seconds, "tv_usec": 0}))
        await self.setsockopt(SOL_SOCKET, SO_SNDTIMEO, timeval.build({"tv_sec": seconds, "tv_usec": 0}))

    async def gettimeout(self) -> int | None:
        return self._timeout

    async def setblocking(self, blocking: bool) -> None:
        opts = (await self._client.symbols.fcntl(self.fd, F_GETFL, 0)).c_uint64
        if not blocking:
            opts |= O_NONBLOCK
        else:
            opts &= ~O_NONBLOCK
        if await self._client.symbols.fcntl(self.fd, F_SETFL, opts) != 0:
            await self._client.raise_errno_exception(f"fcntl() failed: {await self._client.get_last_error()}")
        self._blocking = blocking

    async def getblocking(self) -> bool:
        if self._blocking is None:
            self._blocking = await self._getblocking()

        return self._blocking

    async def _getblocking(self) -> bool:
        return not bool(await self._client.symbols.fcntl(self.fd, F_GETFL, 0) & O_NONBLOCK)

    def __repr__(self) -> str:
        blocking = self._blocking if self._blocking is not None else "<unknown>"
        return f"<{self.__class__.__name__} FD:{self.fd} BLOCKING:{blocking}>"
```

#### send

```
send(buf: bytes | Symbol, size: int | None = None, flags: int = 0) -> int
```

Send bytes from buf on the remote socket fd.

Parameters:

| Name    | Type    | Description                                                 | Default               |
| ------- | ------- | ----------------------------------------------------------- | --------------------- |
| `buf`   | \`bytes | Symbol\`                                                    | buffer to send        |
| `size`  | \`int   | None\`                                                      | If None, use len(buf) |
| `flags` | `int`   | flags for send() syscall. MSG_NOSIGNAL will always be added | `0`                   |

Returns:

| Type  | Description              |
| ----- | ------------------------ |
| `int` | how many bytes were sent |

Source code in `src/rpcclient/rpcclient/core/subsystems/network.py`

```
async def send(self, buf: bytes | Symbol, size: int | None = None, flags: int = 0) -> int:
    """
    Send bytes from buf on the remote socket fd.

    :param buf: buffer to send
    :param size: If None, use len(buf)
    :param flags: flags for send() syscall. MSG_NOSIGNAL will always be added
    :return: how many bytes were sent
    """
    if size is None:
        if isinstance(buf, Symbol):
            raise ValueError("cannot calculate size argument for Symbol objects")
        size = len(buf)
    n = (await self._client.symbols.send(self.fd, buf, size, MSG_NOSIGNAL | flags)).c_int64
    if n < 0:
        if await self._client.get_errno() == EPIPE:
            await self.deallocate()
        await self._client.raise_errno_exception(f"failed to send on fd: {self.fd}")
    return n
```

#### sendall

```
sendall(buf: bytes, flags: int = 0) -> None
```

Send the entire buffer, retrying until all bytes are written.

Source code in `src/rpcclient/rpcclient/core/subsystems/network.py`

```
async def sendall(self, buf: bytes, flags: int = 0) -> None:
    """Send the entire buffer, retrying until all bytes are written."""
    size = len(buf)
    offset = 0
    async with self._client.safe_malloc(size) as block:
        await block.poke(buf)
        while offset < size:
            sent = await self.send(block + offset, size - offset, flags=flags)
            offset += sent
```

#### recv

```
recv(size: int = CHUNK_SIZE, flags: int = 0) -> bytes
```

Receive up to size bytes from the remote socket fd.

Parameters:

| Name    | Type  | Description                                                 | Default      |
| ------- | ----- | ----------------------------------------------------------- | ------------ |
| `size`  | `int` | chunk size                                                  | `CHUNK_SIZE` |
| `flags` | `int` | flags for recv() syscall. MSG_NOSIGNAL will always be added | `0`          |

Returns:

| Type    | Description    |
| ------- | -------------- |
| `bytes` | received bytes |

Source code in `src/rpcclient/rpcclient/core/subsystems/network.py`

```
async def recv(self, size: int = CHUNK_SIZE, flags: int = 0) -> bytes:
    """
    Receive up to size bytes from the remote socket fd.

    :param size: chunk size
    :param flags: flags for recv() syscall. MSG_NOSIGNAL will always be added
    :return: received bytes
    """
    async with self._client.safe_malloc(size) as chunk:
        return await self._recv(chunk, size, flags=flags)
```

#### recvall

```
recvall(size: int, flags: int = 0) -> bytes
```

recv at remote until all buffer is received

Source code in `src/rpcclient/rpcclient/core/subsystems/network.py`

```
async def recvall(self, size: int, flags: int = 0) -> bytes:
    """recv at remote until all buffer is received"""
    buf = b""
    async with self._client.safe_malloc(size) as chunk:
        while len(buf) < size:
            buf += await self._recv(chunk, size - len(buf), flags=flags)
    return buf
```

### Network

Bases: `ClientBound[ClientT_co]`

Source code in `src/rpcclient/rpcclient/core/subsystems/network.py`

```
class Network(ClientBound[ClientT_co]):
    def __init__(self, client: ClientT_co) -> None:
        """
        :param rpcclient.client.client.Client client:
        """
        self._client = client

    async def socket(self, family=AF_INET, socktype=SOCK_STREAM, proto=0) -> int:
        """Create a remote socket and return its file descriptor."""
        result = (await self._client.symbols.socket(family, socktype, proto)).c_int32
        if result < 0:
            await self._client.raise_errno_exception(f"failed to create socket: {result}")
        return result

    async def tcp_connect(self, address: str, port: int) -> Socket:
        """make target connect to given address:port and get socket object"""
        family = AF_INET6 if ":" in address else AF_INET
        sockfd = await self.socket(family=family, socktype=SOCK_STREAM, proto=0)
        if family == AF_INET:
            servaddr = sockaddr_in.build({"sin_addr": pysock.inet_pton(family, address), "sin_port": port})
        else:
            servaddr = sockaddr_in6.build({"sin6_addr": pysock.inet_pton(family, address), "sin6_port": port})
        await self._client.set_errno(0)
        error = (await self._client.symbols.connect(sockfd, servaddr, len(servaddr))).c_int64
        if error == -1:
            await self._client.symbols.close(sockfd)
            await self._client.raise_errno_exception(f"failed connecting to: {address}:{port}")
        return Socket(self._client, sockfd)

    async def unix_connect(self, filename: str) -> Socket:
        """make target connect to given unix path and get socket object"""
        sockfd = await self.socket(family=AF_UNIX, socktype=SOCK_STREAM, proto=0)
        servaddr = sockaddr_un.build({"sun_path": filename})
        await self._client.set_errno(0)
        error = (await self._client.symbols.connect(sockfd, servaddr, len(servaddr))).c_int64
        if error == -1:
            await self._client.symbols.close(sockfd)
            await self._client.raise_errno_exception(f"failed connecting to: {filename}")
        return Socket(self._client, sockfd)

    async def gethostbyname(self, name: str) -> Hostentry | None:
        """Query DNS record. Returns None if not found."""
        aliases = []
        addresses = []
        result = await self._client.symbols.gethostbyname(name)
        if result == 0:
            return None
        result = await parse_hostent(self._client, result)
        p_aliases = result.h_aliases

        i = 0
        while alias := await p_aliases.getindex(i):
            aliases.append(await alias.peek_str())
            i += 1

        addr_list = result.h_addr_list

        i = 0
        while addr := await addr_list.getindex(i):
            addresses.append(pysock.inet_ntoa(await addr.peek(4)))
            i += 1

        return Hostentry(name=result.h_name, aliases=aliases, addresses=addresses)

    async def interfaces(self) -> list[Interface]:
        """get current interfaces"""
        results = []
        async with self._client.safe_calloc(8) as addresses:
            if (await self._client.symbols.getifaddrs(addresses)).c_int64 < 0:
                await self._client.raise_errno_exception("getifaddrs failed")

            current = await parse_ifaddrs(self._client, await addresses.getindex(0))

            while current:
                family = (await current.ifa_addr.parse(sockaddr)).sa_family if current.ifa_addr else None

                if family == AF_INET:
                    address = pysock.inet_ntoa((await current.ifa_addr.parse(sockaddr_in)).sin_addr)
                    netmask = pysock.inet_ntoa((await current.ifa_netmask.parse(sockaddr_in)).sin_addr)
                    broadcast = None
                    if current.ifa_dstaddr:
                        broadcast = pysock.inet_ntoa((await current.ifa_dstaddr.parse(sockaddr_in)).sin_addr)
                    results.append(
                        Interface(name=current.ifa_name, address=address, netmask=netmask, broadcast=broadcast)
                    )

                current = current.ifa_next

            await self._client.symbols.freeifaddrs(await addresses.getindex(0))
        return results
```

#### socket

```
socket(family=AF_INET, socktype=SOCK_STREAM, proto=0) -> int
```

Create a remote socket and return its file descriptor.

Source code in `src/rpcclient/rpcclient/core/subsystems/network.py`

```
async def socket(self, family=AF_INET, socktype=SOCK_STREAM, proto=0) -> int:
    """Create a remote socket and return its file descriptor."""
    result = (await self._client.symbols.socket(family, socktype, proto)).c_int32
    if result < 0:
        await self._client.raise_errno_exception(f"failed to create socket: {result}")
    return result
```

#### tcp_connect

```
tcp_connect(address: str, port: int) -> Socket
```

make target connect to given address:port and get socket object

Source code in `src/rpcclient/rpcclient/core/subsystems/network.py`

```
async def tcp_connect(self, address: str, port: int) -> Socket:
    """make target connect to given address:port and get socket object"""
    family = AF_INET6 if ":" in address else AF_INET
    sockfd = await self.socket(family=family, socktype=SOCK_STREAM, proto=0)
    if family == AF_INET:
        servaddr = sockaddr_in.build({"sin_addr": pysock.inet_pton(family, address), "sin_port": port})
    else:
        servaddr = sockaddr_in6.build({"sin6_addr": pysock.inet_pton(family, address), "sin6_port": port})
    await self._client.set_errno(0)
    error = (await self._client.symbols.connect(sockfd, servaddr, len(servaddr))).c_int64
    if error == -1:
        await self._client.symbols.close(sockfd)
        await self._client.raise_errno_exception(f"failed connecting to: {address}:{port}")
    return Socket(self._client, sockfd)
```

#### unix_connect

```
unix_connect(filename: str) -> Socket
```

make target connect to given unix path and get socket object

Source code in `src/rpcclient/rpcclient/core/subsystems/network.py`

```
async def unix_connect(self, filename: str) -> Socket:
    """make target connect to given unix path and get socket object"""
    sockfd = await self.socket(family=AF_UNIX, socktype=SOCK_STREAM, proto=0)
    servaddr = sockaddr_un.build({"sun_path": filename})
    await self._client.set_errno(0)
    error = (await self._client.symbols.connect(sockfd, servaddr, len(servaddr))).c_int64
    if error == -1:
        await self._client.symbols.close(sockfd)
        await self._client.raise_errno_exception(f"failed connecting to: {filename}")
    return Socket(self._client, sockfd)
```

#### gethostbyname

```
gethostbyname(name: str) -> Hostentry | None
```

Query DNS record. Returns None if not found.

Source code in `src/rpcclient/rpcclient/core/subsystems/network.py`

```
async def gethostbyname(self, name: str) -> Hostentry | None:
    """Query DNS record. Returns None if not found."""
    aliases = []
    addresses = []
    result = await self._client.symbols.gethostbyname(name)
    if result == 0:
        return None
    result = await parse_hostent(self._client, result)
    p_aliases = result.h_aliases

    i = 0
    while alias := await p_aliases.getindex(i):
        aliases.append(await alias.peek_str())
        i += 1

    addr_list = result.h_addr_list

    i = 0
    while addr := await addr_list.getindex(i):
        addresses.append(pysock.inet_ntoa(await addr.peek(4)))
        i += 1

    return Hostentry(name=result.h_name, aliases=aliases, addresses=addresses)
```

#### interfaces

```
interfaces() -> list[Interface]
```

get current interfaces

Source code in `src/rpcclient/rpcclient/core/subsystems/network.py`

```
async def interfaces(self) -> list[Interface]:
    """get current interfaces"""
    results = []
    async with self._client.safe_calloc(8) as addresses:
        if (await self._client.symbols.getifaddrs(addresses)).c_int64 < 0:
            await self._client.raise_errno_exception("getifaddrs failed")

        current = await parse_ifaddrs(self._client, await addresses.getindex(0))

        while current:
            family = (await current.ifa_addr.parse(sockaddr)).sa_family if current.ifa_addr else None

            if family == AF_INET:
                address = pysock.inet_ntoa((await current.ifa_addr.parse(sockaddr_in)).sin_addr)
                netmask = pysock.inet_ntoa((await current.ifa_netmask.parse(sockaddr_in)).sin_addr)
                broadcast = None
                if current.ifa_dstaddr:
                    broadcast = pysock.inet_ntoa((await current.ifa_dstaddr.parse(sockaddr_in)).sin_addr)
                results.append(
                    Interface(name=current.ifa_name, address=address, netmask=netmask, broadcast=broadcast)
                )

            current = current.ifa_next

        await self._client.symbols.freeifaddrs(await addresses.getindex(0))
    return results
```

## Processes

## rpcclient.core.subsystems.processes

### Processes

Bases: `ClientBound[ClientT_co]`

Source code in `src/rpcclient/rpcclient/core/subsystems/processes.py`

```
class Processes(ClientBound[ClientT_co]):
    def __init__(self, client: ClientT_co) -> None:
        """
        process manager
        :param rpcclient.darwin_client.Client client: client
        """
        self._client = client

    async def kill(self, pid: int, sig: int = SIGTERM) -> None:
        """Send a signal to a remote process."""
        if await self._client.symbols.kill(pid, sig) != 0:
            raise BadReturnValueError(f"kill({pid}, {sig}) failed ({await self._client.get_last_error()})")

    async def waitpid(self, pid: int, flags: int = 0) -> int:
        """Wait for a remote process to change state and return status."""
        async with self._client.safe_malloc(8) as stat_loc:
            err = (await self._client.symbols.waitpid(pid, stat_loc, flags)).c_int64
            if err == -1:
                raise BadReturnValueError(f"waitpid(): returned {err} ({await self._client.get_last_error()})")
            return int(await stat_loc.getindex(0))
```

#### kill

```
kill(pid: int, sig: int = SIGTERM) -> None
```

Send a signal to a remote process.

Source code in `src/rpcclient/rpcclient/core/subsystems/processes.py`

```
async def kill(self, pid: int, sig: int = SIGTERM) -> None:
    """Send a signal to a remote process."""
    if await self._client.symbols.kill(pid, sig) != 0:
        raise BadReturnValueError(f"kill({pid}, {sig}) failed ({await self._client.get_last_error()})")
```

#### waitpid

```
waitpid(pid: int, flags: int = 0) -> int
```

Wait for a remote process to change state and return status.

Source code in `src/rpcclient/rpcclient/core/subsystems/processes.py`

```
async def waitpid(self, pid: int, flags: int = 0) -> int:
    """Wait for a remote process to change state and return status."""
    async with self._client.safe_malloc(8) as stat_loc:
        err = (await self._client.symbols.waitpid(pid, stat_loc, flags)).c_int64
        if err == -1:
            raise BadReturnValueError(f"waitpid(): returned {err} ({await self._client.get_last_error()})")
        return int(await stat_loc.getindex(0))
```

## WebDAV mounting

## rpcclient.core.subsystems.webdav.WebDav

Bases: `ClientBound[ClientT_co]`

Serve a remote path over WebDAV for local mounting.

Source code in `src/rpcclient/rpcclient/core/subsystems/webdav.py`

```
class WebDav(ClientBound[ClientT_co]):
    """Serve a remote path over WebDAV for local mounting."""

    def __init__(self, client: ClientT_co) -> None:
        self._client = client

    async def serve(self, path: str, *, host: str = "127.0.0.1", port: int = 0, readonly: bool = False) -> WebDavServer:
        """Start a WebDAV server exposing the remote ``path``.

        :param path: remote directory to serve.
        :param host: local interface to bind (default: loopback).
        :param port: local TCP port; 0 picks a free port.
        :param readonly: expose the path read-only.
        :return: a running-server handle with ``url`` and ``stop()``.
        """
        for name in ("asgi_webdav", "uvicorn", "uvicorn.error", "uvicorn.access"):
            logging.getLogger(name).setLevel(logging.WARNING)

        config = generate_config_from_dict({
            "account_mapping": [{"username": "anonymous", "password": "", "permissions": ["+"]}],
            "anonymous": {
                "enable": True,
                "user": {"username": "anonymous", "password": "", "permissions": ["+"]},
                "allow_missing_auth_header": True,
            },
            "provider_mapping": [],
            "logging": {"enable": False},
        })
        reinit_global_config(config)

        app = DAVApp(config)
        provider = RpcFsProvider(client=self._client, root=path, config=config, prefix=DAVPath("/"), read_only=readonly)
        app.web_dav.prefix_provider_mapping = [
            PrefixProviderInfo(
                prefix=DAVPath("/"),
                prefix_weight=1,
                provider=provider,
                home_dir=False,
                read_only=readonly,
                ignore_property_extra=True,
            )
        ]

        uv_config = uvicorn.Config(app, host=host, port=port, log_level="warning", lifespan="off")
        server = uvicorn.Server(uv_config)
        task = asyncio.ensure_future(server.serve())
        while not server.started:
            await asyncio.sleep(0.02)
        bound_port = server.servers[0].sockets[0].getsockname()[1]
        return WebDavServer(server, task, host, bound_port)
```

### serve

```
serve(path: str, *, host: str = '127.0.0.1', port: int = 0, readonly: bool = False) -> WebDavServer
```

Start a WebDAV server exposing the remote `path`.

Parameters:

| Name       | Type   | Description                                  | Default       |
| ---------- | ------ | -------------------------------------------- | ------------- |
| `path`     | `str`  | remote directory to serve.                   | *required*    |
| `host`     | `str`  | local interface to bind (default: loopback). | `'127.0.0.1'` |
| `port`     | `int`  | local TCP port; 0 picks a free port.         | `0`           |
| `readonly` | `bool` | expose the path read-only.                   | `False`       |

Returns:

| Type           | Description                                  |
| -------------- | -------------------------------------------- |
| `WebDavServer` | a running-server handle with url and stop(). |

Source code in `src/rpcclient/rpcclient/core/subsystems/webdav.py`

```
async def serve(self, path: str, *, host: str = "127.0.0.1", port: int = 0, readonly: bool = False) -> WebDavServer:
    """Start a WebDAV server exposing the remote ``path``.

    :param path: remote directory to serve.
    :param host: local interface to bind (default: loopback).
    :param port: local TCP port; 0 picks a free port.
    :param readonly: expose the path read-only.
    :return: a running-server handle with ``url`` and ``stop()``.
    """
    for name in ("asgi_webdav", "uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.WARNING)

    config = generate_config_from_dict({
        "account_mapping": [{"username": "anonymous", "password": "", "permissions": ["+"]}],
        "anonymous": {
            "enable": True,
            "user": {"username": "anonymous", "password": "", "permissions": ["+"]},
            "allow_missing_auth_header": True,
        },
        "provider_mapping": [],
        "logging": {"enable": False},
    })
    reinit_global_config(config)

    app = DAVApp(config)
    provider = RpcFsProvider(client=self._client, root=path, config=config, prefix=DAVPath("/"), read_only=readonly)
    app.web_dav.prefix_provider_mapping = [
        PrefixProviderInfo(
            prefix=DAVPath("/"),
            prefix_weight=1,
            provider=provider,
            home_dir=False,
            read_only=readonly,
            ignore_property_extra=True,
        )
    ]

    uv_config = uvicorn.Config(app, host=host, port=port, log_level="warning", lifespan="off")
    server = uvicorn.Server(uv_config)
    task = asyncio.ensure_future(server.serve())
    while not server.started:
        await asyncio.sleep(0.02)
    bound_port = server.servers[0].sockets[0].getsockname()[1]
    return WebDavServer(server, task, host, bound_port)
```

## rpcclient.core.subsystems.webdav.WebDavServer

Handle for a running WebDAV server.

Source code in `src/rpcclient/rpcclient/core/subsystems/webdav.py`

```
class WebDavServer:
    """Handle for a running WebDAV server."""

    def __init__(self, uvicorn_server: Any, task: Any, host: str, port: int) -> None:
        self._server = uvicorn_server
        self._task = task
        self.host = host
        self.port = port

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    async def stop(self) -> None:
        self._server.should_exit = True
        await self._task
```

## Symbols

## rpcclient.core.symbol

### AbstractSymbol

Bases: `int`, `ABC`

Abstract wrapper for a remote symbol object

Source code in `src/rpcclient/rpcclient/core/symbol.py`

```
class AbstractSymbol(int, abc.ABC):
    """Abstract wrapper for a remote symbol object"""

    @final
    def __new__(cls, value: int, *args, **kwargs) -> Self:
        if not isinstance(value, int):
            raise TypeError(f"expected int, got {type(value).__qualname__}")

        value &= 0xFFFFFFFFFFFFFFFF

        return super().__new__(cls, value)

    @abc.abstractmethod
    def _symbol_from_value(self, value: int) -> Self:
        """
        Returns the given value as a symbol.
        The symbol's type can change depending on the value and/or the symbol's state.

        :param value: Symbol address
        :return: Symbol object.
        :rtype: Symbol
        """

    @contextmanager
    def change_item_size(self, new_item_size: int) -> Generator[None]:
        """
        Temporarily change item size
        :param new_item_size: Temporary item size
        """
        save_item_size = self.item_size
        self.item_size = new_item_size
        try:
            yield
        finally:
            self.item_size = save_item_size

    @abc.abstractmethod
    async def peek(self, count: int, offset: int = 0) -> bytes: ...

    @abc.abstractmethod
    async def poke(self, buf: bytes, offset: int = 0) -> Any: ...

    @abc.abstractmethod
    async def peek_str(self, encoding="utf-8") -> str:
        """peek string at given address"""

    def close(self) -> None:
        """Construct compliance."""
        pass

    def seek(self, offset: int, whence: int) -> None:
        """Construct compliance."""
        if whence == os.SEEK_CUR:
            self._offset += offset
        elif whence == os.SEEK_SET:
            self._offset = offset - self
        else:
            raise OSError("Unsupported whence")

    async def read(self, count: int) -> bytes:
        """Construct compliance."""
        val = await (self + self._offset).peek(count)
        self._offset += count
        return val

    async def write(self, buf: bytes) -> None:
        """Construct compliance."""
        val = await (self + self._offset).poke(buf)
        self._offset += len(buf)
        return val

    def tell(self) -> Self:
        """Construct compliance."""
        return self + self._offset

    @property
    @abc.abstractmethod
    def arch(self) -> object: ...

    async def disass(self, size=40) -> list[CsInsn]:
        """peek disassembled lines of 'size' bytes"""
        cs = (
            Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
            if self.arch == ARCH_ARM64
            # assume x86_64 by default
            else Cs(CS_ARCH_X86, CS_MODE_LITTLE_ENDIAN | CS_MODE_64)
        )

        return list(cs.disasm(await self.peek(size), self))

    @property
    def c_int64(self) -> int:
        """cast to c_int64"""
        return ctypes.c_int64(self).value

    @property
    def c_uint64(self) -> int:
        """cast to c_uint64"""
        return ctypes.c_uint64(self).value

    @property
    def c_int32(self) -> int:
        """cast to c_int32"""
        return ctypes.c_int32(self).value

    @property
    def c_uint32(self) -> int:
        """cast to c_uint32"""
        return ctypes.c_uint32(self).value

    @property
    def c_int16(self) -> int:
        """cast to c_int16"""
        return ctypes.c_int16(self).value

    @property
    def c_uint16(self) -> int:
        """cast to c_uint16"""
        return ctypes.c_uint16(self).value

    @property
    def c_bool(self) -> bool:
        """cast to c_bool"""
        return ctypes.c_bool(self).value

    @abc.abstractmethod
    async def get_dl_info(self) -> "Container": ...

    async def dl_info(self) -> "Container":
        return await self.get_dl_info()

    async def name(self) -> str:
        return (await self.get_dl_info()).dli_sname

    async def filename(self) -> str:
        return (await self.get_dl_info()).dli_fname

    @property
    @abc.abstractmethod
    def endianness(self) -> str: ...

    async def getindex(self, index: int, *indices: int) -> Self:
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        new_symbol = self._symbol_from_value(
            struct.unpack(self.endianness + fmt, await self.peek(self.item_size, offset=index * self.item_size))[0]
        )
        if indices:
            return await new_symbol.getindex(*indices)
        return new_symbol

    async def setindex(self, index: int, value) -> None:
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        value = struct.pack(self.endianness + fmt, int(value))
        await self.poke(value, offset=index * self.item_size)

    def __getitem__(self, item: int) -> Coroutine[Any, Any, Self]:
        """Read a remote item: ``await sym[i]`` (awaitable alias for ``getindex``)."""
        return self.getindex(item)

    def __setitem__(self, item: int, value) -> None:
        raise TypeError(
            "item assignment can't be awaited; use `await sym.setindex(index, value)` instead of `sym[index] = value`"
        )

    async def parse(self, struct: "Construct[ParsedType, Any]") -> "ParsedType":
        return struct.parse(await self.peek(struct.sizeof()))

    def __add__(self, other) -> Self:
        try:
            return self._symbol_from_value(int(self) + other)
        except TypeError:
            return int(self) + other

    def __radd__(self, other) -> Self:
        return self.__add__(other)

    def __sub__(self, other) -> Self:
        try:
            return self._symbol_from_value(int(self) - other)
        except TypeError:
            return int(self) - other

    def __rsub__(self, other) -> Self:
        try:
            return self._symbol_from_value(other - int(self))
        except TypeError:
            return other - int(self)

    def __mul__(self, other) -> Self:
        try:
            return self._symbol_from_value(int(self) * other)
        except TypeError:
            return int(self) * other

    def __rmul__(self, other) -> Self:
        return self.__mul__(other)

    def __truediv__(self, other) -> Self:
        return self._symbol_from_value(int(self) / other)

    def __floordiv__(self, other) -> Self:
        return self._symbol_from_value(int(self) // other)

    def __mod__(self, other) -> Self:
        return self._symbol_from_value(int(self) % other)

    def __and__(self, other) -> Self:
        return self._symbol_from_value(int(self) & other)

    def __or__(self, other) -> Self:
        return self._symbol_from_value(int(self) | other)

    def __xor__(self, other) -> Self:
        return self._symbol_from_value(int(self) ^ other)

    def __repr__(self) -> str:
        return f"<{type(self).__name__}: {hex(self)}>"

    def __str__(self) -> str:
        return hex(self)
```

#### c_int64

```
c_int64: int
```

cast to c_int64

#### c_uint64

```
c_uint64: int
```

cast to c_uint64

#### c_int32

```
c_int32: int
```

cast to c_int32

#### c_uint32

```
c_uint32: int
```

cast to c_uint32

#### c_int16

```
c_int16: int
```

cast to c_int16

#### c_uint16

```
c_uint16: int
```

cast to c_uint16

#### c_bool

```
c_bool: bool
```

cast to c_bool

#### change_item_size

```
change_item_size(new_item_size: int) -> Generator[None]
```

Temporarily change item size

Parameters:

| Name            | Type  | Description         | Default    |
| --------------- | ----- | ------------------- | ---------- |
| `new_item_size` | `int` | Temporary item size | *required* |

Source code in `src/rpcclient/rpcclient/core/symbol.py`

```
@contextmanager
def change_item_size(self, new_item_size: int) -> Generator[None]:
    """
    Temporarily change item size
    :param new_item_size: Temporary item size
    """
    save_item_size = self.item_size
    self.item_size = new_item_size
    try:
        yield
    finally:
        self.item_size = save_item_size
```

#### peek_str

```
peek_str(encoding='utf-8') -> str
```

peek string at given address

Source code in `src/rpcclient/rpcclient/core/symbol.py`

```
@abc.abstractmethod
async def peek_str(self, encoding="utf-8") -> str:
    """peek string at given address"""
```

#### close

```
close() -> None
```

Construct compliance.

Source code in `src/rpcclient/rpcclient/core/symbol.py`

```
def close(self) -> None:
    """Construct compliance."""
    pass
```

#### seek

```
seek(offset: int, whence: int) -> None
```

Construct compliance.

Source code in `src/rpcclient/rpcclient/core/symbol.py`

```
def seek(self, offset: int, whence: int) -> None:
    """Construct compliance."""
    if whence == os.SEEK_CUR:
        self._offset += offset
    elif whence == os.SEEK_SET:
        self._offset = offset - self
    else:
        raise OSError("Unsupported whence")
```

#### read

```
read(count: int) -> bytes
```

Construct compliance.

Source code in `src/rpcclient/rpcclient/core/symbol.py`

```
async def read(self, count: int) -> bytes:
    """Construct compliance."""
    val = await (self + self._offset).peek(count)
    self._offset += count
    return val
```

#### write

```
write(buf: bytes) -> None
```

Construct compliance.

Source code in `src/rpcclient/rpcclient/core/symbol.py`

```
async def write(self, buf: bytes) -> None:
    """Construct compliance."""
    val = await (self + self._offset).poke(buf)
    self._offset += len(buf)
    return val
```

#### tell

```
tell() -> Self
```

Construct compliance.

Source code in `src/rpcclient/rpcclient/core/symbol.py`

```
def tell(self) -> Self:
    """Construct compliance."""
    return self + self._offset
```

#### disass

```
disass(size=40) -> list[CsInsn]
```

peek disassembled lines of 'size' bytes

Source code in `src/rpcclient/rpcclient/core/symbol.py`

```
async def disass(self, size=40) -> list[CsInsn]:
    """peek disassembled lines of 'size' bytes"""
    cs = (
        Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        if self.arch == ARCH_ARM64
        # assume x86_64 by default
        else Cs(CS_ARCH_X86, CS_MODE_LITTLE_ENDIAN | CS_MODE_64)
    )

    return list(cs.disasm(await self.peek(size), self))
```

### Symbol

Bases: `AbstractSymbol`

wrapper for a remote symbol object

Source code in `src/rpcclient/rpcclient/core/symbol.py`

```
class Symbol(AbstractSymbol):
    """wrapper for a remote symbol object"""

    @readonly
    def _client(self) -> "CoreClient[Self]": ...

    def __init__(self, value: int, client: "CoreClient[Self]") -> None:
        """
        Create a Symbol object.
        :param value: Symbol address.
        :param client: client.
        :return: Symbol object.
        :rtype: Symbol
        """
        self.retval_bit_count: int = RETVAL_BIT_COUNT
        self.is_retval_signed: bool = True
        self.item_size: int = 8

        # private members
        __class__._client.set(self, client)
        self._offset: int = 0

    def _symbol_from_value(self, value: int) -> Self:
        """
        Returns the given value as a symbol.
        The symbol's type can change depending on the value and/or the symbol's state.

        :param value: Symbol address
        :return: Symbol object.
        :rtype: Symbol
        """
        return type(self)(value, cast("CoreClient", self._client))

    async def peek(self, count: int, offset: int = 0) -> bytes:
        return await self._client.peek(self + offset, count)

    async def poke(self, buf: bytes, offset: int = 0) -> Any:
        return await self._client.poke(self + offset, buf)

    async def peek_str(self, encoding="utf-8") -> str:
        """peek string at given address"""
        str_len = await self._client.symbols.strlen(self)
        return (await self.peek(str_len)).decode(encoding)

    @property
    def arch(self) -> object:
        return self._client.arch

    async def get_dl_info(self) -> "Container":
        dl_info = Dl_info(self._client)
        sizeof = dl_info.sizeof()
        async with self._client.safe_malloc(sizeof) as info:
            if await self._client.symbols.dladdr(self, info) == 0:
                await self._client.raise_errno_exception(f"failed to extract info for: {self}")
            return dl_info.parse(await info.read(sizeof))

    @property
    def endianness(self) -> str:
        return self._client._endianness

    async def resolve(self) -> Self:
        """Return this symbol unchanged.

        This method exists to allow calling `resolve()` on an object that may be either a symbol or a `LazySymbol`.
        """
        return self

    @overload
    async def call(
        self,
        *args: "RemoteCallArg",
        return_float64: Literal[False] = False,
        return_float32: Literal[False] = False,
        return_raw: Literal[False] = False,
        va_list_index: int | None = None,
    ) -> Self: ...
    @overload
    async def call(
        self, *args: "RemoteCallArg", return_float64: Literal[True], va_list_index: int | None = None
    ) -> float: ...
    @overload
    async def call(
        self, *args: "RemoteCallArg", return_float32: Literal[True], va_list_index: int | None = None
    ) -> float: ...
    @overload
    async def call(
        self, *args: "RemoteCallArg", return_raw: Literal[True], va_list_index: int | None = None
    ) -> Any: ...
    @overload
    async def call(self, *args: "RemoteCallArg", **kwargs) -> "float | Self | Any": ...
    async def call(self, *args: "RemoteCallArg", **kwargs) -> "float | Self | Any":
        """Call this symbol as a function pointer."""
        return await self._client.call(self, args, **kwargs)

    __call__ = call
```

#### peek_str

```
peek_str(encoding='utf-8') -> str
```

peek string at given address

Source code in `src/rpcclient/rpcclient/core/symbol.py`

```
async def peek_str(self, encoding="utf-8") -> str:
    """peek string at given address"""
    str_len = await self._client.symbols.strlen(self)
    return (await self.peek(str_len)).decode(encoding)
```

#### resolve

```
resolve() -> Self
```

Return this symbol unchanged.

This method exists to allow calling `resolve()` on an object that may be either a symbol or a `LazySymbol`.

Source code in `src/rpcclient/rpcclient/core/symbol.py`

```
async def resolve(self) -> Self:
    """Return this symbol unchanged.

    This method exists to allow calling `resolve()` on an object that may be either a symbol or a `LazySymbol`.
    """
    return self
```

#### call

```
call(*args: RemoteCallArg, return_float64: Literal[False] = False, return_float32: Literal[False] = False, return_raw: Literal[False] = False, va_list_index: int | None = None) -> Self
```

```
call(*args: RemoteCallArg, return_float64: Literal[True], va_list_index: int | None = None) -> float
```

```
call(*args: RemoteCallArg, return_float32: Literal[True], va_list_index: int | None = None) -> float
```

```
call(*args: RemoteCallArg, return_raw: Literal[True], va_list_index: int | None = None) -> Any
```

```
call(*args: RemoteCallArg, **kwargs) -> float | Self | Any
```

```
call(*args: RemoteCallArg, **kwargs) -> float | Self | Any
```

Call this symbol as a function pointer.

Source code in `src/rpcclient/rpcclient/core/symbol.py`

```
async def call(self, *args: "RemoteCallArg", **kwargs) -> "float | Self | Any":
    """Call this symbol as a function pointer."""
    return await self._client.call(self, args, **kwargs)
```

## Capturing file descriptors

## rpcclient.core.capture_fd

### CaptureFD

Bases: `Allocated['CoreClient[SymbolT_co]']`, `Generic[SymbolT_co]`

Context manager, capturing output to a given `fd`. Read from it using the `read()` method.

Source code in `src/rpcclient/rpcclient/core/capture_fd.py`

```
class CaptureFD(Allocated["CoreClient[SymbolT_co]"], Generic[SymbolT_co]):
    """
    Context manager, capturing output to a given `fd`. Read from it using the `read()` method.
    """

    def __init__(self, client: "CoreClient[SymbolT_co]", fd: int, sock_buf_size: int | None = None) -> None:
        """
        sock_buf_size is required for captures above 6KB, as any write above this value would block until a read is performed.

        :param rpcclient.client.client.Client client: Current client
        :param fd: FD to capture
        :param sock_buf_size: Buffer size for the capture socket, if not specified, default value is used.
        """
        self._client = client
        self.fd: int = fd
        self._backupfd: int | None = None
        self._socket_pair: tuple[int, int] | None = None
        self._sock_buf_size: int | None = sock_buf_size

    async def _allocate(self) -> None:
        async with self._client.safe_malloc(FD_SIZE * 2) as socket_pair:
            socket_pair.item_size = FD_SIZE
            if await self._client.symbols.socketpair(AF_UNIX, SOCK_STREAM, 0, socket_pair) != 0:
                await self._client.raise_errno_exception("socketpair failed")
            self._socket_pair = ((await socket_pair.getindex(0)).c_int32, (await socket_pair.getindex(1)).c_int32)
        if self._sock_buf_size is not None:
            await Socket(self._client, self._socket_pair[0]).setbufsize(self._sock_buf_size)
        self._backupfd = (await self._client.symbols.dup(self.fd)).c_int32
        if self._backupfd == -1:
            self._backupfd = None
            await self._client.raise_errno_exception("dup fd failed")
        if await self._client.symbols.dup2(self._socket_pair[0], self.fd) < 0:
            await self._client.raise_errno_exception("dup2 sock-fd failed")

    async def _deallocate(self) -> None:
        if self._backupfd is not None:
            if await self._client.symbols.dup2(self._backupfd, self.fd) < 0:
                await self._client.raise_errno_exception("dup2 backup-fd failed")
            if await self._client.symbols.close(self._backupfd) != 0:
                await self._client.raise_errno_exception("close backupfd failed")
            self._backupfd = None
        if self._socket_pair is not None:
            if await self._client.symbols.close(self._socket_pair[0]) != 0:
                await self._client.raise_errno_exception(f"close _socket_pair[0] {self._socket_pair[0]} failed")
            if await self._client.symbols.close(self._socket_pair[1]) != 0:
                await self._client.raise_errno_exception(f"close _socket_pair[1] {self._socket_pair[1]} failed")
            self._socket_pair = None

    async def read(self) -> bytes:
        """Read the bytes captured from `fd` so far."""
        data = b""
        if self._socket_pair is not None:
            async with self._client.safe_malloc(READ_SIZE) as buff:
                read = READ_SIZE
                while read == READ_SIZE:
                    async with self._client.safe_malloc(pollfd.sizeof()) as pfds:
                        await pfds.poke(pollfd.build({"fd": self._socket_pair[1], "events": POLLIN, "revents": 0}))
                        if await self._client.symbols.poll(pfds, 1, 0) != 1:
                            return data
                    read = (await self._client.symbols.read(self._socket_pair[1], buff, READ_SIZE)).c_int32
                    if read == -1:
                        await self._client.raise_errno_exception("read fd failed")
                    data += await buff.peek(read)
        return data
```

#### read

```
read() -> bytes
```

Read the bytes captured from `fd` so far.

Source code in `src/rpcclient/rpcclient/core/capture_fd.py`

```
async def read(self) -> bytes:
    """Read the bytes captured from `fd` so far."""
    data = b""
    if self._socket_pair is not None:
        async with self._client.safe_malloc(READ_SIZE) as buff:
            read = READ_SIZE
            while read == READ_SIZE:
                async with self._client.safe_malloc(pollfd.sizeof()) as pfds:
                    await pfds.poke(pollfd.build({"fd": self._socket_pair[1], "events": POLLIN, "revents": 0}))
                    if await self._client.symbols.poll(pfds, 1, 0) != 1:
                        return data
                read = (await self._client.symbols.read(self._socket_pair[1], buff, READ_SIZE)).c_int32
                if read == -1:
                    await self._client.raise_errno_exception("read fd failed")
                data += await buff.peek(read)
    return data
```

## Exceptions

## rpcclient.exceptions

### RpcClientException

Bases: `Exception`

general exception

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcClientException(Exception):
    """general exception"""

    pass
```

### InvalidServerVersionMagicError

Bases: `RpcClientException`

server handshake failed due to an invalid magic

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class InvalidServerVersionMagicError(RpcClientException):
    """server handshake failed due to an invalid magic"""

    pass
```

### ResponseNotFoundError

Bases: `RpcClientException`

Response not found

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class ResponseNotFoundError(RpcClientException):
    """Response not found"""

    pass
```

### SubsystemInitError

Bases: `RpcClientException`

Raised when unavailable subsystems are used.

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class SubsystemInitError(RpcClientException):
    """Raised when unavailable subsystems are used."""

    pass
```

### ServerResponseError

Bases: `RpcClientException`

Server returned error

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class ServerResponseError(RpcClientException):
    """Server returned error"""

    pass
```

### ServerDiedError

Bases: `RpcClientException`

server became disconnected during an operation

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class ServerDiedError(RpcClientException):
    """server became disconnected during an operation"""

    pass
```

### SymbolAbsentError

Bases: `RpcClientException`

trying to access a symbol which is not exported from any library currently loaded into the server's memory

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class SymbolAbsentError(RpcClientException):
    """trying to access a symbol which is not exported from any library currently loaded into the server's memory"""

    pass
```

### ProcessSymbolAbsentError

Bases: `RpcClientException`

trying to access a symbol which is not exported from any library currently loaded into the process's memory

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class ProcessSymbolAbsentError(RpcClientException):
    """trying to access a symbol which is not exported from any library currently loaded into the process's memory"""

    pass
```

### ArgumentError

Bases: `RpcClientException`

at least one of the supplied arguments for a given function was invalid

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class ArgumentError(RpcClientException):
    """at least one of the supplied arguments for a given function was invalid"""

    pass
```

### BadReturnValueError

Bases: `RpcClientException`

remote c function returned an error

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class BadReturnValueError(RpcClientException):
    """remote c function returned an error"""

    pass
```

### NoSuchPreferenceError

Bases: `RpcClientException`

attempt to read a preference data which doesn't exist

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class NoSuchPreferenceError(RpcClientException):
    """attempt to read a preference data which doesn't exist"""

    pass
```

### CfSerializationError

Bases: `RpcClientException`

failed to encode/decode a cfobject into/from a python object

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class CfSerializationError(RpcClientException):
    """failed to encode/decode a cfobject into/from a python object"""

    pass
```

### SpawnError

Bases: `RpcClientException`

failed to spawn a child process

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class SpawnError(RpcClientException):
    """failed to spawn a child process"""

    pass
```

### FailedToConnectError

Bases: `RpcClientException`

failed to connect to rpcserver

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class FailedToConnectError(RpcClientException):
    """failed to connect to rpcserver"""

    pass
```

### UnrecognizedSelectorError

Bases: `RpcClientException`

tried to access a non-existing objc object selector

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class UnrecognizedSelectorError(RpcClientException):
    """tried to access a non-existing objc object selector"""

    pass
```

### GettingObjectiveCClassError

Bases: `RpcClientException`

failed to create an objc class wrapper for a given object

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class GettingObjectiveCClassError(RpcClientException):
    """failed to create an objc class wrapper for a given object"""

    pass
```

### MissingLibraryError

Bases: `RpcClientException`

a required library could not be found

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class MissingLibraryError(RpcClientException):
    """a required library could not be found"""

    pass
```

### NoEntitlementsError

Bases: `RpcClientException`

binary contains no entitlements

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class NoEntitlementsError(RpcClientException):
    """binary contains no entitlements"""

    pass
```

### HarGlobalNotFoundError

Bases: `RpcClientException`

Failed to find Harlogger global

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class HarGlobalNotFoundError(RpcClientException):
    """Failed to find Harlogger global"""

    pass
```

### ElementNotFoundError

Bases: `RpcClientException`

Failed to find element

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class ElementNotFoundError(RpcClientException):
    """Failed to find element"""

    pass
```

### FirstElementNotFoundError

Bases: `ElementNotFoundError`

Failed to find the first element

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class FirstElementNotFoundError(ElementNotFoundError):
    """Failed to find the first element"""

    pass
```

### LastElementNotFoundError

Bases: `ElementNotFoundError`

Failed to find the last element

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class LastElementNotFoundError(ElementNotFoundError):
    """Failed to find the last element"""

    pass
```

### LaunchError

Bases: `BadReturnValueError`

failed to launch a child process

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class LaunchError(BadReturnValueError):
    """failed to launch a child process"""

    pass
```

### RpcFileExistsError

Bases: `BadReturnValueError`

RPC version for FileExistsError (errno = EEXIST)

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcFileExistsError(BadReturnValueError):
    """RPC version for FileExistsError (errno = EEXIST)"""

    pass
```

### RpcFileNotFoundError

Bases: `BadReturnValueError`

RPC version for FileNotFoundError (errno = ENOENTRY)

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcFileNotFoundError(BadReturnValueError):
    """RPC version for FileNotFoundError (errno = ENOENTRY)"""

    pass
```

### RpcBrokenPipeError

Bases: `BadReturnValueError`

RPC version for BrokenPipeError (errno = EPIPE)

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcBrokenPipeError(BadReturnValueError):
    """RPC version for BrokenPipeError (errno = EPIPE)"""

    pass
```

### RpcNotEmptyError

Bases: `BadReturnValueError`

raised when errno = ENOTEMPTY

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcNotEmptyError(BadReturnValueError):
    """raised when errno = ENOTEMPTY"""

    pass
```

### RpcIsADirectoryError

Bases: `BadReturnValueError`

RPC version for IsADirectoryError (errno = ENOTEMPTY)

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcIsADirectoryError(BadReturnValueError):
    """RPC version for IsADirectoryError (errno = ENOTEMPTY)"""

    pass
```

### RpcNotADirectoryError

Bases: `BadReturnValueError`

RPC version for NotADirectoryError (errno = ENOTDIR)

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcNotADirectoryError(BadReturnValueError):
    """RPC version for NotADirectoryError (errno = ENOTDIR)"""

    pass
```

### RpcPermissionError

Bases: `BadReturnValueError`

RPC version for PermissionError (errno = EPERM)

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcPermissionError(BadReturnValueError):
    """RPC version for PermissionError (errno = EPERM)"""

    pass
```

### RpcAccessibilityTurnedOffError

Bases: `BadReturnValueError`

Application AX and Automation is turned off

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcAccessibilityTurnedOffError(BadReturnValueError):
    """Application AX and Automation is turned off"""

    pass
```

### RpcFailedToRecordError

Bases: `BadReturnValueError`

An attempt to record has failed

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcFailedToRecordError(BadReturnValueError):
    """An attempt to record has failed"""

    pass
```

### RpcFailedToPlayError

Bases: `BadReturnValueError`

An attempt to play has failed

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcFailedToPlayError(BadReturnValueError):
    """An attempt to play has failed"""

    pass
```

### RpcResourceTemporarilyUnavailableError

Bases: `BadReturnValueError`

raised when errno = EAGAIN

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcResourceTemporarilyUnavailableError(BadReturnValueError):
    """raised when errno = EAGAIN"""

    pass
```

### RpcConnectionRefusedError

Bases: `BadReturnValueError`

RPC version for ConnectionRefusedError (errno = ECONNREFUSED)

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcConnectionRefusedError(BadReturnValueError):
    """RPC version for ConnectionRefusedError (errno = ECONNREFUSED)"""

    pass
```

### RpcDeadClientError

Bases: `BadReturnValueError`

RPC client in a dead state

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcDeadClientError(BadReturnValueError):
    """RPC client in a dead state"""

    pass
```

### RpcFailedLaunchingAppError

Bases: `BadReturnValueError`

Failed to launch application

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcFailedLaunchingAppError(BadReturnValueError):
    """Failed to launch application"""

    pass
```

### RpcAppleScriptError

Bases: `BadReturnValueError`

Failed to execute given AppleScript

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcAppleScriptError(BadReturnValueError):
    """Failed to execute given AppleScript"""

    pass
```

### RpcXpcError

Bases: `BadReturnValueError`

XPC-related error

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcXpcError(BadReturnValueError):
    """XPC-related error"""

    pass
```

### RpcXpcSerializationError

Bases: `RpcXpcError`

Failed to serialize/deserialize XPC message

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcXpcSerializationError(RpcXpcError):
    """Failed to serialize/deserialize XPC message"""

    pass
```

### RpcSetDeveloperModeError

Bases: `BadReturnValueError`

Failed to set Developer Mode

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcSetDeveloperModeError(BadReturnValueError):
    """Failed to set Developer Mode"""

    pass
```

### RpcFailedToGetPrimaryAppError

Bases: `BadReturnValueError`

Failed to get [AXElement primaryApp]

Source code in `src/rpcclient/rpcclient/exceptions.py`

```
class RpcFailedToGetPrimaryAppError(BadReturnValueError):
    """Failed to get [AXElement primaryApp]"""

    pass
```
