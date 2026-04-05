import contextlib
import dataclasses
import errno
import logging
import posixpath
import re
import struct
from collections import namedtuple
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Generic, NoReturn, cast
from typing_extensions import Self

import zyncio
from construct import Array, Container, Int32ul

from rpcclient.clients.darwin._types import DarwinClientT_co, DarwinSymbolT_co
from rpcclient.clients.darwin.consts import (
    EXC_MASK_ALL,
    EXC_TYPES_COUNT,
    MACH_PORT_TYPE_ALL_RIGHTS,
    MACH_PORT_TYPE_DEAD_NAME,
    MACH_PORT_TYPE_DNREQUEST,
    MACH_PORT_TYPE_PORT_SET,
    MACH_PORT_TYPE_RECEIVE,
    MACH_PORT_TYPE_SEND,
    MACH_PORT_TYPE_SEND_ONCE,
    TASK_DYLD_INFO,
    TASK_FLAVOR_READ,
    TASK_VM_INFO,
    THREAD_IDENTIFIER_INFO,
    VM_FLAGS_ANYWHERE,
    ARMThreadFlavors,
    kCSNow,
    x86_THREAD_STATE64,
)
from rpcclient.clients.darwin.structs import (
    ARM_THREAD_STATE64_COUNT,
    FAT_CIGAM,
    FAT_MAGIC,
    LOAD_COMMAND_TYPE,
    MAXPATHLEN,
    PROC_PIDFDPIPEINFO,
    PROC_PIDFDPSHMINFO,
    PROC_PIDFDSOCKETINFO,
    PROC_PIDFDVNODEPATHINFO,
    PROC_PIDLISTFDS,
    PROC_PIDTASKALLINFO,
    PROX_FDTYPE_KQUEUE,
    PROX_FDTYPE_PIPE,
    PROX_FDTYPE_PSHM,
    PROX_FDTYPE_SOCKET,
    PROX_FDTYPE_VNODE,
    TASK_DYLD_INFO_COUNT,
    TASK_VM_INFO_COUNT,
    THREAD_IDENTIFIER_INFO_COUNT,
    all_image_infos_t,
    arm_thread_state64_t,
    dyld_image_info_t,
    fat_header,
    ipc_info_name_t,
    mach_header_t,
    mach_port_t,
    pid_t,
    pipe_info,
    proc_fdinfo,
    proc_taskallinfo,
    procargs2_t,
    pshm_fdinfo,
    so_family_t,
    so_kind_t,
    socket_fdinfo,
    task_dyld_info_data_t,
    task_vm_info_data_t,
    thread_identifier_info,
    vnode_fdinfowithpath,
    x86_thread_state64_t,
)
from rpcclient.clients.darwin.symbol import BaseDarwinSymbol
from rpcclient.core._types import ClientBound
from rpcclient.core.structs.consts import SEEK_SET, SIGKILL, SIGTERM
from rpcclient.core.structs.generic import Dl_info
from rpcclient.core.subsystems.processes import Processes
from rpcclient.core.subsystems.sysctl import CTL, KERN
from rpcclient.core.symbol import AbstractSymbol
from rpcclient.exceptions import (
    ArgumentError,
    BadReturnValueError,
    ProcessSymbolAbsentError,
    RpcClientException,
    SymbolAbsentError,
    UnrecognizedSelectorError,
)
from rpcclient.protos.rpc_pb2 import ARCH_ARM64
from rpcclient.utils import cached_async_method, zync_sleep


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient

_CF_STRING_ARRAY_PREFIX_LEN = len('    "')
_CF_STRING_ARRAY_SUFFIX_LEN = len('",')
_BACKTRACE_FRAME_REGEX = re.compile(r"\[\s*(\d+)\] (0x[0-9a-f]+)\s+\{(.+?) \+ (.+?)\} (.*)")

FdStruct = namedtuple("FdStruct", "fd struct")

logger = logging.getLogger(__name__)

CDHASH_SIZE = 20
CHUNK_SIZE = 1024 * 64
APP_SUFFIX = ".app/"


@dataclasses.dataclass
class Fd:
    fd: int


@dataclasses.dataclass
class KQueueFd(Fd):
    pass


@dataclasses.dataclass
class PipeFd(Fd):
    pass


@dataclasses.dataclass
class SharedMemoryFd(Fd):
    path: str


@dataclasses.dataclass
class FileFd(Fd):
    path: str


@dataclasses.dataclass
class UnixFd(Fd):
    path: str


@dataclasses.dataclass
class SocketFd(Fd):
    pass


@dataclasses.dataclass
class Ipv4SocketFd(SocketFd):
    local_address: str
    local_port: int
    remote_address: str
    remote_port: int  # when remote 0, the socket is for listening


@dataclasses.dataclass
class Ipv6SocketFd(SocketFd):
    local_address: str
    local_port: int
    remote_address: str
    remote_port: int  # when remote 0, the socket is for listening


@dataclasses.dataclass
class Ipv4TcpFd(Ipv4SocketFd):
    pass


@dataclasses.dataclass
class Ipv6TcpFd(Ipv6SocketFd):
    pass


@dataclasses.dataclass
class Ipv4UdpFd(Ipv4SocketFd):
    pass


@dataclasses.dataclass
class Ipv6UdpFd(Ipv6SocketFd):
    pass


Image = namedtuple("Image", "address path")

SOCKET_TYPE_DATACLASS = {
    so_family_t.AF_INET: {
        so_kind_t.SOCKINFO_TCP: Ipv4TcpFd,
        so_kind_t.SOCKINFO_IN: Ipv4UdpFd,
    },
    so_family_t.AF_INET6: {
        so_kind_t.SOCKINFO_TCP: Ipv6TcpFd,
        so_kind_t.SOCKINFO_IN: Ipv6UdpFd,
    },
}


class Thread(ClientBound[DarwinClientT_co]):
    def __init__(self, client: DarwinClientT_co, thread_id: int) -> None:
        """Initialize a thread wrapper for the given client and thread id."""
        self._client = client
        self._thread_id: int = thread_id

    @property
    def thread_id(self) -> int:
        """Return the Mach thread id."""
        return self._thread_id

    @zyncio.zmethod
    async def get_state(self) -> Container:
        """Return the architecture-specific thread state."""
        raise NotImplementedError()

    @zyncio.zmethod
    async def set_state(self, state: dict) -> None:
        """Set the architecture-specific thread state."""
        raise NotImplementedError()

    @zyncio.zmethod
    async def resume(self) -> None:
        """Resume execution of the thread."""
        raise NotImplementedError()

    @zyncio.zmethod
    async def suspend(self) -> None:
        """Suspend execution of the thread."""
        raise NotImplementedError()

    def __repr__(self) -> str:
        """Return a debug representation of the thread."""
        return f"<{self.__class__.__name__} TID:{self._thread_id}>"


class IntelThread64(Thread[DarwinClientT_co]):
    @zyncio.zmethod
    async def get_state(self) -> Container:
        """Fetch the x86_64 thread state."""
        async with (
            self._client.safe_malloc.z(x86_thread_state64_t.sizeof()) as p_state,
            self._client.safe_malloc.z(x86_thread_state64_t.sizeof()) as p_thread_state_count,
        ):
            await p_thread_state_count.setindex(0, x86_thread_state64_t.sizeof() // Int32ul.sizeof())
            if await self._client.symbols.thread_get_state.z(
                self._thread_id, x86_THREAD_STATE64, p_state, p_thread_state_count
            ):
                raise BadReturnValueError("thread_get_state() failed")
            return await p_state.parse.z(x86_thread_state64_t)

    @zyncio.zmethod
    async def set_state(self, state: dict) -> None:
        """Set the x86_64 thread state."""
        if await self._client.symbols.thread_set_state.z(
            self._thread_id,
            x86_THREAD_STATE64,
            x86_thread_state64_t.build(state),
            x86_thread_state64_t.sizeof() // Int32ul.sizeof(),
        ):
            raise BadReturnValueError("thread_set_state() failed")


class ArmThread64(Thread[DarwinClientT_co]):
    @zyncio.zmethod
    async def get_state(self) -> Container:
        """Fetch the ARM64 thread state."""
        async with (
            self._client.safe_malloc.z(arm_thread_state64_t.sizeof()) as p_state,
            self._client.safe_malloc.z(arm_thread_state64_t.sizeof()) as p_thread_state_count,
        ):
            await p_thread_state_count.setindex(0, ARM_THREAD_STATE64_COUNT)
            if await self._client.symbols.thread_get_state.z(
                self._thread_id, ARMThreadFlavors.ARM_THREAD_STATE64, p_state, p_thread_state_count
            ):
                raise BadReturnValueError("thread_get_state() failed")
            return await p_state.parse.z(arm_thread_state64_t)

    @zyncio.zmethod
    async def set_state(self, state: dict) -> None:
        """Set the ARM64 thread state."""
        if await self._client.symbols.thread_set_state.z(
            self._thread_id,
            ARMThreadFlavors.ARM_THREAD_STATE64,
            arm_thread_state64_t.build(state),
            ARM_THREAD_STATE64_COUNT,
        ):
            raise BadReturnValueError("thread_set_state() failed")

    @zyncio.zmethod
    async def suspend(self) -> None:
        """Suspend execution of the ARM64 thread."""
        if await self._client.symbols.thread_suspend.z(self._thread_id):
            raise BadReturnValueError("thread_suspend() failed")

    @zyncio.zmethod
    async def resume(self) -> None:
        """Resume execution of the ARM64 thread."""
        if await self._client.symbols.thread_resume.z(self._thread_id):
            raise BadReturnValueError("thread_resume() failed")


@dataclasses.dataclass
class Region(Generic[DarwinSymbolT_co]):
    region_type: str
    start: "ProcessSymbol[DarwinSymbolT_co]"
    end: int
    vsize: str | None
    protection: str
    protection_max: str
    region_detail: str | None

    @property
    def size(self) -> int:
        """Return the region size in bytes."""
        return self.end - self.start


@dataclasses.dataclass
class LoadedClass:
    name: str
    type_name: str
    binary_path: str


@dataclasses.dataclass
class Frame:
    depth: int
    address: int
    section: str
    offset: int
    symbol_name: str

    def __repr__(self):
        """Return a formatted frame representation."""
        return (
            f"<{self.__class__.__name__} [{self.depth:3}] 0x{self.address:x} ({self.section} + 0x{self.offset:x}) "
            f"{self.symbol_name}>"
        )


@dataclasses.dataclass(kw_only=True)
class Backtrace:
    flavor: str
    time_start: float | None = None
    time_end: float | None = None
    pid: int
    thread_id: int
    dispatch_queue_serial_num: int
    frames: list[Frame]

    @staticmethod
    async def _from_backtrace(vmu_backtrace: BaseDarwinSymbol) -> "Backtrace":
        """Parse a VMU backtrace description into structured fields."""
        backtrace = await (await vmu_backtrace.objc_call.z("description")).py.z(str)
        match = re.match(
            (
                r"VMUBacktrace \(Flavor: (?P<flavor>.+?) Simple Time: (?P<time>.+?) "
                r"Process: (?P<pid>\d+) Thread: (?P<thread_id>.+?)  Dispatch queue serial num: "
                r"(?P<dispatch_queue_serial_num>\d+)\)"
            ),
            backtrace,
        )
        assert match is not None

        return Backtrace(
            flavor=match.group("flavor"),
            pid=int(match.group("pid")),
            thread_id=int(match.group("thread_id"), 16),
            dispatch_queue_serial_num=int(match.group("dispatch_queue_serial_num")),
            frames=[
                Frame(
                    depth=int(frame[0]),
                    address=int(frame[1], 0),
                    section=frame[2],
                    offset=int(frame[3], 0),
                    symbol_name=frame[4],
                )
                for frame in re.findall(_BACKTRACE_FRAME_REGEX, backtrace)
            ],
        )

    def __repr__(self) -> str:
        """Return a formatted backtrace representation."""
        buf = f"<{self.__class__.__name__} PID: {self.pid} TID: {self.thread_id}\n"
        for frame in self.frames:
            buf += f"    {frame}\n"
        buf += ">"
        return buf


class ProcessSymbol(AbstractSymbol, ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, value: int, process: "Process[DarwinSymbolT_co]") -> None:
        self._client: BaseDarwinClient[DarwinSymbolT_co] = process._client
        self.process: Process[DarwinSymbolT_co] = process

    def _symbol_from_value(self, value: int) -> Self:
        """Clone this symbol for the given value."""
        return type(self)(value, self.process)

    @zyncio.zmethod
    async def peek(self, count: int, offset: int = 0) -> bytes:
        """Read bytes from process memory at this address."""
        return await self.process.peek.z(self + offset, count)

    @zyncio.zmethod
    async def poke(self, buf: bytes, offset: int = 0) -> None:
        """Write bytes to process memory at this address."""
        return await self.process.poke.z(self + offset, buf)

    @zyncio.zmethod
    async def peek_str(self, encoding="utf-8") -> str:
        """peek string at given address"""
        return await self.process.peek_str.z(self, encoding)

    @zyncio.zproperty
    async def dl_info(self) -> Container:
        """Raise because dl_info is not available for remote process symbols."""
        raise NotImplementedError("dl_info isn't implemented for remote process symbols")

    @zyncio.zproperty
    async def name(self) -> str:
        """Return the symbol name for this address."""
        return await self.process.get_symbol_name.z(self)

    @zyncio.zproperty
    async def filename(self) -> str:
        """Return the image path containing this symbol."""
        return (await self.process.get_symbol_image.z(await type(self).name(self))).path

    @zyncio.zmethod
    async def get_dl_info(self) -> "Container":
        dl_info = Dl_info(self._client)
        sizeof = dl_info.sizeof()
        async with self._client.safe_malloc.z(sizeof) as info:
            if await self._client.symbols.dladdr.z(self, info) == 0:
                await self._client.raise_errno_exception.z(f"failed to extract info for: {self}")
            return dl_info.parse(await info.read.z(sizeof))

    @property
    def arch(self) -> object:
        return self._client.arch

    @property
    def endianness(self) -> str:
        return self._client._endianness

    def call(self, *args, **kwargs) -> NoReturn:
        """Disallow calling a process symbol as a function."""
        raise RpcClientException("ProcessSymbol is not callable")

    __call__ = call


@dataclasses.dataclass
class MachPortThreadInfo:
    thread_ids: list[int]


@dataclasses.dataclass
class MachPortInfo:
    task: int
    pid: int
    name: int
    rights: list[str]
    ipc_object: int
    dead: bool
    proc_name: str | None = None
    thread_info: MachPortThreadInfo | None = None

    @property
    def has_recv_right(self) -> bool:
        """Return True if the port has a receive right."""
        return "recv" in self.rights

    @property
    def has_send_right(self) -> bool:
        """Return True if the port has a send right."""
        return "send" in self.rights


@dataclasses.dataclass
class MachPortCrossRefInfo:
    name: int
    ipc_object: int
    recv_right_pid: int
    recv_right_proc_name: str | None


class SymbolOwner(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(
        self,
        client: "BaseDarwinClient[DarwinSymbolT_co]",
        process: "Process[DarwinSymbolT_co]",
        symbol_owner_opaque1: ProcessSymbol[DarwinSymbolT_co],
        symbol_owner_opaque2: ProcessSymbol[DarwinSymbolT_co],
    ) -> None:
        """Initialize a symbol owner wrapper."""
        self._client: BaseDarwinClient[DarwinSymbolT_co] = client
        self._process: Process[DarwinSymbolT_co] = process
        self.symbol_owner_opaque1: ProcessSymbol[DarwinSymbolT_co] = symbol_owner_opaque1
        self.symbol_owner_opaque2: ProcessSymbol[DarwinSymbolT_co] = symbol_owner_opaque2

    @zyncio.zmethod
    async def get_symbol_address(self, name: str) -> ProcessSymbol[DarwinSymbolT_co]:
        """Resolve a symbol address by name."""
        symbol = await self._client.symbols.CSSymbolOwnerGetSymbolWithName.z(
            self.symbol_owner_opaque1,
            self.symbol_owner_opaque2,
            name,
            return_raw=True,
        )

        return self._process.get_process_symbol(await self._client.symbols.CSSymbolGetRange.z(symbol.x0, symbol.x1))


class Symbolicator(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(
        self,
        client: "BaseDarwinClient[DarwinSymbolT_co]",
        process: "Process[DarwinSymbolT_co]",
        symbolicator_opaque1: ProcessSymbol[DarwinSymbolT_co],
        symbolicator_opaque2: ProcessSymbol[DarwinSymbolT_co],
    ) -> None:
        """Initialize a symbolicator wrapper."""
        self._client: BaseDarwinClient[DarwinSymbolT_co] = client
        self._process: Process[DarwinSymbolT_co] = process
        self.symbolicator_opaque1: ProcessSymbol[DarwinSymbolT_co] = symbolicator_opaque1
        self.symbolicator_opaque2: ProcessSymbol[DarwinSymbolT_co] = symbolicator_opaque2

    @zyncio.zmethod
    async def get_symbol_owner(self, library_basename: str) -> SymbolOwner[DarwinSymbolT_co]:
        """Resolve a symbol owner by library basename."""
        symbol_owner = await self._client.symbols.CSSymbolicatorGetSymbolOwnerWithNameAtTime.z(
            self.symbolicator_opaque1,
            self.symbolicator_opaque2,
            library_basename,
            kCSNow,
            return_raw=True,
        )
        return SymbolOwner(self._client, self._process, symbol_owner.x0, symbol_owner.x1)


class Process(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    PEEK_STR_CHUNK_SIZE = 0x100

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]", pid: int) -> None:
        """Initialize a process wrapper for a pid."""
        self._client = client
        self._pid: int = pid

        if self._client.arch == ARCH_ARM64:
            self._thread_class = ArmThread64
        else:
            self._thread_class = IntelThread64

    @zyncio.zmethod
    async def kill(self, sig: int = SIGTERM) -> None:
        """Send a signal to the remote process."""
        return await self._client.processes.kill.z(self._pid, sig)

    @zyncio.zmethod
    async def waitpid(self, flags: int = 0) -> int:
        """Wait for the remote process to change state and return status."""
        return await self._client.processes.waitpid.z(self._pid, flags)

    @zyncio.zmethod
    async def peek(self, address: int, size: int) -> bytes:
        """peek at memory address"""
        async with self._client.safe_malloc.z(size) as buf, self._client.safe_malloc.z(8) as p_size:
            await p_size.setindex(0, size)
            if await self._client.symbols.vm_read_overwrite.z(
                await type(self).task_read(self), address, size, buf, p_size
            ):
                raise BadReturnValueError("vm_read() failed")
            return await buf.peek.z(size)

    @zyncio.zmethod
    async def peek_str(self, address: int, encoding="utf-8") -> str:
        """peek string at memory address"""
        size = self.PEEK_STR_CHUNK_SIZE
        buf = b""

        while size:
            try:
                buf += await self.peek.z(address, size)
                if b"\x00" in buf:
                    return buf.split(b"\x00", 1)[0].decode(encoding)
                address += size
            except BadReturnValueError:
                size = size // 2
        else:
            raise RuntimeError("Failed to find string terminator")

    @zyncio.zmethod
    async def poke(self, address: int, buf: bytes) -> None:
        """poke at memory address"""
        if await self._client.symbols.vm_write.z(await type(self).task(self), address, buf, len(buf)):
            raise BadReturnValueError("vm_write() failed")

    @zyncio.zmethod
    async def get_symbol_name(self, address: int) -> str:
        """Resolve a symbol name for the given address."""
        if self._client.arch != ARCH_ARM64:
            raise NotImplementedError("implemented only on ARCH_ARM64")
        result = await (await type(self).vmu_object_identifier(self)).objc_call_raw.z("symbolForAddress:", address)
        if result.x0 == 0 and result.x1 == 0:
            raise SymbolAbsentError()
        return await (await self._client.symbols.CSSymbolGetName.z(result.x0, result.x1)).peek_str.z()

    @zyncio.zmethod
    async def get_symbol_image(self, name: str) -> Image:
        """Find the image containing the named symbol."""
        for image in await type(self).images(self):
            result = await self.get_symbol_address.z(name, posixpath.basename(image.path))
            if result:
                return image

        raise ProcessSymbolAbsentError()

    @zyncio.zmethod
    async def get_symbol_class_info(self, address: int) -> DarwinSymbolT_co:
        """Return Objective-C class info for the given address."""
        return await (await type(self).vmu_object_identifier(self)).objc_call.z(
            "classInfoForMemory:length:", address, 8
        )

    @zyncio.zmethod
    async def get_symbol_address(
        self, name: str, lib: str | None = None
    ) -> DarwinSymbolT_co | ProcessSymbol[DarwinSymbolT_co]:
        """Resolve a symbol address, optionally within a library."""
        if lib is not None:
            address = (
                await (await type(self).vmu_object_identifier(self)).objc_call.z(
                    "addressOfSymbol:inLibrary:", name, lib
                )
            ).c_uint64
            if self.pid == await self._client.get_pid.z():
                return self._client.symbol(address)
            return self.get_process_symbol(address)

        image = await self.get_symbol_image.z(name)
        return await self.get_symbol_address.z(name, posixpath.basename(image.path))

    @zyncio.zgeneratormethod
    async def loaded_classes(self) -> AsyncGenerator[LoadedClass]:
        """Yield realized Objective-C classes for the process."""
        realized_classes = await (await type(self).vmu_object_identifier(self)).objc_call.z("realizedClasses")

        for i in range(1, await realized_classes.objc_call.z("count") + 1):
            class_info = await realized_classes.objc_call.z("classInfoForIndex:", i)
            name = await (await class_info.objc_call.z("className")).py.z(str)
            type_name = await (await class_info.objc_call.z("typeName")).py.z(str)
            binary_path = await (await class_info.objc_call.z("binaryPath")).py.z(str)
            yield LoadedClass(name=name, type_name=type_name, binary_path=binary_path)

    @zyncio.zproperty
    async def images(self) -> list[Image]:
        """get loaded image list"""
        result = []

        async with (
            self._client.safe_malloc.z(task_dyld_info_data_t.sizeof()) as dyld_info,
            self._client.safe_calloc.z(8) as count,
        ):
            await count.setindex(0, TASK_DYLD_INFO_COUNT)
            if await self._client.symbols.task_info.z(
                await type(self).task_read(self), TASK_DYLD_INFO, dyld_info, count
            ):
                raise BadReturnValueError("task_info(TASK_DYLD_INFO) failed")
            dyld_info_data = await dyld_info.parse.z(task_dyld_info_data_t)

        all_image_infos = all_image_infos_t.parse(
            await self.peek.z(dyld_info_data.all_image_info_addr, dyld_info_data.all_image_info_size)
        )

        buf = await self.peek.z(all_image_infos.infoArray, all_image_infos.infoArrayCount * dyld_image_info_t.sizeof())
        for image in Array(all_image_infos.infoArrayCount, dyld_image_info_t).parse(buf):
            path = await self.peek_str.z(image.imageFilePath)
            result.append(Image(address=self.get_process_symbol(image.imageLoadAddress), path=path))
        return result

    @zyncio.zproperty
    async def app_images(self) -> list[Image]:
        """Return images that belong to the app bundle."""
        return [image for image in await type(self).images(self) if APP_SUFFIX in image.path]

    @zyncio.zproperty
    async def threads(self) -> list[Thread]:
        """Return the list of threads in the process."""
        result = []

        async with self._client.safe_malloc.z(8) as threads, self._client.safe_malloc.z(4) as count:
            count.item_size = 4
            if await self._client.symbols.task_threads.z(await type(self).task_read(self), threads, count):
                raise BadReturnValueError("task_threads() failed")

            for tid in Array((await count.getindex(0)).c_uint32, Int32ul).parse(
                await (await threads.getindex(0)).peek.z(await count.getindex(0) * 4)
            ):
                result.append(self._thread_class(self._client, tid))

        return result

    @property
    def pid(self) -> int:
        """get pid"""
        return self._pid

    @zyncio.zproperty
    async def fds(self) -> list[Fd]:
        """get a list of process opened file descriptors"""
        result = []
        for fdstruct in await self.fd_structs.z():
            fd = fdstruct.fd
            parsed = fdstruct.struct

            if fd.proc_fdtype == PROX_FDTYPE_VNODE:
                result.append(FileFd(fd=fd.proc_fd, path=parsed.pvip.vip_path))

            elif fd.proc_fdtype == PROX_FDTYPE_KQUEUE:
                result.append(KQueueFd(fd=fd.proc_fd))

            elif fd.proc_fdtype == PROX_FDTYPE_PIPE:
                result.append(PipeFd(fd=fd.proc_fd))

            elif fd.proc_fdtype == PROX_FDTYPE_PSHM:
                result.append(SharedMemoryFd(fd=fd.proc_fd, path=parsed.pshminfo.pshm_name))

            elif fd.proc_fdtype == PROX_FDTYPE_SOCKET:
                if parsed.psi.soi_kind in (so_kind_t.SOCKINFO_TCP, so_kind_t.SOCKINFO_IN):
                    correct_class = SOCKET_TYPE_DATACLASS[parsed.psi.soi_family][parsed.psi.soi_kind]

                    if parsed.psi.soi_kind == so_kind_t.SOCKINFO_TCP:
                        info = parsed.psi.soi_proto.pri_tcp.tcpsi_ini
                    else:
                        info = parsed.psi.soi_proto.pri_in
                    result.append(
                        correct_class(
                            fd=fd.proc_fd,
                            local_address=info.insi_laddr.ina_46.i46a_addr4,
                            local_port=info.insi_lport,
                            remote_address=info.insi_faddr.ina_46.i46a_addr4,
                            remote_port=info.insi_fport,
                        )
                    )

                elif parsed.psi.soi_kind == so_kind_t.SOCKINFO_UN:
                    result.append(UnixFd(fd=fd.proc_fd, path=parsed.psi.soi_proto.pri_un.unsi_addr.ua_sun.sun_path))

        return result

    @zyncio.zmethod
    async def fd_structs(self) -> list[FdStruct]:
        """get a list of process opened file descriptors as raw structs"""
        result = []
        size = await self._client.symbols.proc_pidinfo.z(self.pid, PROC_PIDLISTFDS, 0, 0, 0)

        vi_size = 8196  # should be enough for all structs
        async with self._client.safe_malloc.z(vi_size) as vi_buf:
            async with self._client.safe_malloc.z(size) as fdinfo_buf:
                size = int(await self._client.symbols.proc_pidinfo.z(self.pid, PROC_PIDLISTFDS, 0, fdinfo_buf, size))
                if not size:
                    raise BadReturnValueError("proc_pidinfo(PROC_PIDLISTFDS) failed")

                for fd in Array(size // proc_fdinfo.sizeof(), proc_fdinfo).parse(await fdinfo_buf.peek.z(size)):
                    if fd.proc_fdtype == PROX_FDTYPE_VNODE:
                        # file
                        vs = await self._client.symbols.proc_pidfdinfo.z(
                            self.pid, fd.proc_fd, PROC_PIDFDVNODEPATHINFO, vi_buf, vi_size
                        )
                        if not vs:
                            if await self._client.get_errno.z() == errno.EBADF:
                                # lsof treats this as fine
                                continue
                            raise BadReturnValueError(
                                f"proc_pidinfo(PROC_PIDFDVNODEPATHINFO) failed for fd: {fd.proc_fd} "
                                f"({await self._client.get_last_error.z()})"
                            )

                        result.append(
                            FdStruct(
                                fd=fd,
                                struct=vnode_fdinfowithpath.parse(await vi_buf.peek.z(vnode_fdinfowithpath.sizeof())),
                            )
                        )

                    elif fd.proc_fdtype == PROX_FDTYPE_KQUEUE:
                        result.append(FdStruct(fd=fd, struct=None))

                    elif fd.proc_fdtype == PROX_FDTYPE_SOCKET:
                        # socket
                        vs = await self._client.symbols.proc_pidfdinfo.z(
                            self.pid, fd.proc_fd, PROC_PIDFDSOCKETINFO, vi_buf, vi_size
                        )
                        if not vs:
                            if await self._client.get_errno.z() == errno.EBADF:
                                # lsof treats this as fine
                                continue
                            raise BadReturnValueError(
                                f"proc_pidinfo(PROC_PIDFDSOCKETINFO) failed ({await self._client.get_last_error.z()})"
                            )

                        result.append(FdStruct(fd=fd, struct=socket_fdinfo.parse(await vi_buf.peek.z(vi_size))))

                    elif fd.proc_fdtype == PROX_FDTYPE_PIPE:
                        # pipe
                        vs = await self._client.symbols.proc_pidfdinfo.z(
                            self.pid, fd.proc_fd, PROC_PIDFDPIPEINFO, vi_buf, vi_size
                        )
                        if not vs:
                            if await self._client.get_errno.z() == errno.EBADF:
                                # lsof treats this as fine
                                continue
                            raise BadReturnValueError(
                                f"proc_pidinfo(PROC_PIDFDPIPEINFO) failed ({await self._client.get_last_error.z()})"
                            )

                        result.append(FdStruct(fd=fd, struct=pipe_info.parse(await vi_buf.peek.z(pipe_info.sizeof()))))

                    elif fd.proc_fdtype == PROX_FDTYPE_PSHM:
                        vs = await self._client.symbols.proc_pidfdinfo.z(
                            self.pid, fd.proc_fd, PROC_PIDFDPSHMINFO, vi_buf, vi_size
                        )
                        if not vs:
                            if await self._client.get_errno.z() == errno.EBADF:
                                continue
                            raise BadReturnValueError(
                                f"proc_pidinfo(PROC_PIDFDPSHMINFO) failed ({await self._client.get_last_error.z()})"
                            )

                        result.append(
                            FdStruct(fd=fd, struct=pshm_fdinfo.parse(await vi_buf.peek.z(pshm_fdinfo.sizeof())))
                        )

            return result

    @zyncio.zmethod
    async def task_all_info(self) -> Container:
        """get a list of process opened file descriptors"""
        async with self._client.safe_malloc.z(proc_taskallinfo.sizeof()) as pti:
            if not await self._client.symbols.proc_pidinfo.z(
                self.pid, PROC_PIDTASKALLINFO, 0, pti, proc_taskallinfo.sizeof()
            ):
                raise BadReturnValueError("proc_pidinfo(PROC_PIDTASKALLINFO) failed")
            return await pti.parse.z(proc_taskallinfo)

    @zyncio.zmethod
    async def task_vm_info(self) -> Container:
        """get TASK_VM_INFO via task_info."""
        async with (
            self._client.safe_malloc.z(task_vm_info_data_t.sizeof()) as vm_info,
            self._client.safe_calloc.z(8) as count,
        ):
            await count.setindex(0, TASK_VM_INFO_COUNT)
            if await self._client.symbols.task_info.z(await type(self).task_read(self), TASK_VM_INFO, vm_info, count):
                raise BadReturnValueError("task_info(TASK_VM_INFO) failed")
            return await vm_info.parse.z(task_vm_info_data_t)

    @zyncio.zmethod
    async def backtraces(self) -> list[Backtrace]:
        """Collect backtraces for all threads in the process."""
        result = []
        backtraces = await (await self._client.symbols.objc_getClass.z("VMUSampler")).objc_call.z(
            "sampleAllThreadsOfTask:", await type(self).task_read(self)
        )
        for i in range(await backtraces.objc_call.z("count")):
            bt = await backtraces.objc_call.z("objectAtIndex:", i)
            result.append(await Backtrace._from_backtrace(bt))
        return result

    @zyncio.zproperty
    @cached_async_method
    async def vmu_proc_info(self) -> DarwinSymbolT_co:
        """Return the VMUProcInfo object for this task."""
        VMUProcInfo = await self._client.symbols.objc_getClass.z("VMUProcInfo")
        return await (await (VMUProcInfo).objc_call.z("alloc")).objc_call.z(
            "initWithTask:", await type(self).task_read(self)
        )

    @zyncio.zproperty
    @cached_async_method
    async def vmu_region_identifier(self: "Process[DarwinSymbolT_co]") -> DarwinSymbolT_co:
        """Return the VMUVMRegionIdentifier object for this task."""

        VMUVMRegionIdentifier = await self._client.symbols.objc_getClass.z("VMUVMRegionIdentifier")
        return await (await (VMUVMRegionIdentifier).objc_call.z("alloc")).objc_call.z(
            "initWithTask:", await type(self).task_read(self)
        )

    @zyncio.zproperty
    @cached_async_method
    async def vmu_object_identifier(self) -> DarwinSymbolT_co:
        """Return the VMUObjectIdentifier object for this task."""
        VMUObjectIdentifier = await self._client.symbols.objc_getClass.z("VMUObjectIdentifier")
        return await (await (VMUObjectIdentifier).objc_call.z("alloc")).objc_call.z(
            "initWithTask:", await type(self).task_read(self)
        )

    @zyncio.zproperty
    @cached_async_method
    async def symbolicator(self) -> Symbolicator[DarwinSymbolT_co]:
        """Return a symbolicator for this task."""
        symbolicator = await self._client.symbols.CSSymbolicatorCreateWithTask.z(
            await type(self).task_read(self), return_raw=True
        )
        return Symbolicator(self._client, self, symbolicator.x0, symbolicator.x1)

    @zyncio.zproperty
    @cached_async_method
    async def task_read(self) -> int:
        """Return the task read port for this process."""
        self_task_port = await self._client.symbols.mach_task_self.z()

        if self.pid == await self._client.get_pid.z():
            return self_task_port

        async with self._client.safe_malloc.z(8) as p_task:
            ret = await self._client.symbols.task_read_for_pid.z(self_task_port, self.pid, p_task)
            if ret:
                raise BadReturnValueError("task_read_for_pid() failed")
            return (await p_task.getindex(0)).c_int64

    @zyncio.zproperty
    @cached_async_method
    async def task(self) -> int:
        """Return the full task port for this process."""
        self_task_port = await self._client.symbols.mach_task_self.z()

        if self.pid == await self._client.get_pid.z():
            return self_task_port

        async with self._client.safe_malloc.z(8) as p_task:
            if await self._client.symbols.task_for_pid.z(self_task_port, self.pid, p_task):
                raise BadReturnValueError("task_for_pid() failed")
            return (await p_task.getindex(0)).c_int64

    @zyncio.zproperty
    @cached_async_method
    async def path(self) -> str | None:
        """call proc_pidpath(filename, ...) at remote. review xnu header for more details."""
        async with self._client.safe_malloc.z(MAXPATHLEN) as path:
            path_len = await self._client.symbols.proc_pidpath.z(self.pid, path, MAXPATHLEN)
            return (await path.peek.z(path_len)).decode() if path_len else None

    @zyncio.zproperty
    @cached_async_method
    async def basename(self) -> str | None:
        """Return the basename of the process path."""
        path = await type(self).path(self)
        return PurePath(path).name if path else None

    @cached_async_method
    async def _get_pbsd(self) -> Container:
        return (await self.task_all_info.z()).pbsd

    @zyncio.zproperty
    async def name(self) -> str:
        """Return the process name from task info."""
        return (await self._get_pbsd()).pbi_name

    @zyncio.zproperty
    async def ppid(self) -> int:
        """Return the parent process id."""
        return (await self._get_pbsd()).pbi_ppid

    @zyncio.zproperty
    async def uid(self) -> int:
        """Return the process user id."""
        return (await self._get_pbsd()).pbi_uid

    @zyncio.zproperty
    async def gid(self) -> int:
        """Return the process group id."""
        return (await self._get_pbsd()).pbi_gid

    @zyncio.zproperty
    async def ruid(self) -> int:
        """Return the real user id."""
        return (await self._get_pbsd()).pbi_ruid

    @zyncio.zproperty
    async def rgid(self) -> int:
        """Return the real group id."""
        return (await self._get_pbsd()).pbi_rgid

    _start_time: datetime | None = None

    @zyncio.zproperty
    async def start_time(self) -> datetime:
        """Return the process start time."""
        if self._start_time is None:
            if self._client.arch != ARCH_ARM64:
                raise NotImplementedError("implemented only on ARCH_ARM64")
            val = await (await type(self).vmu_proc_info(self)).objc_call_raw.z("startTime")
            tv_sec = val.x0
            tv_nsec = val.x1
            self._start_time = datetime.fromtimestamp(tv_sec + (tv_nsec / (10**9)))

        return self._start_time

    @zyncio.zproperty
    async def parent(self) -> Self:
        """Return a Process wrapper for the parent pid."""
        return type(self)(self._client, await type(self).ppid(self))

    @zyncio.zproperty
    async def environ(self) -> list[str]:
        """Return the process environment variables."""
        return await (await (await type(self).vmu_proc_info(self)).objc_call.z("envVars")).py.z(list)

    @zyncio.zproperty
    async def arguments(self) -> list[str]:
        """Return the process argument list."""
        return await (await (await type(self).vmu_proc_info(self)).objc_call.z("arguments")).py.z(list)

    @zyncio.zproperty
    async def raw_procargs2(self) -> bytes:
        """Return the raw PROCARGS2 sysctl buffer."""
        return await self._client.sysctl.get.z(CTL.KERN, KERN.PROCARGS2, self.pid)

    @zyncio.zproperty
    async def procargs2(self) -> Container:
        """Parse and return the PROCARGS2 buffer."""
        return procargs2_t.parse(await type(self).raw_procargs2(self))

    @zyncio.zmethod
    async def get_regions(self) -> list[Region[DarwinSymbolT_co]]:
        """Return the list of VM regions for the process."""
        result: list[Region[DarwinSymbolT_co]] = []

        # remove the '()' wrapping the list:
        #   (
        #       "item1",
        #       "item2",
        #   )
        regions_sym = await (await type(self).vmu_region_identifier(self)).objc_call.z("regions")
        buf = cast(str, await type(regions_sym).cfdesc(regions_sym)).split("\n")[1:-1]

        for line in buf:
            # remove line prefix and suffix and split into words
            line = line[_CF_STRING_ARRAY_PREFIX_LEN:-_CF_STRING_ARRAY_SUFFIX_LEN].split()
            i = 0

            region_type = line[i]
            i += 1

            while "-" not in line[i]:
                # skip till address range
                i += 1

            address_range = line[i]
            i += 1
            if not address_range.startswith("0x"):
                continue
            start, end = address_range.split("-")

            start = int(start, 16)
            end = int(end, 16)
            vsize = None
            if "V=" in line[i]:
                vsize = line[i].split("V=", 1)[1].split("]", 1)[0]

            while "/" not in line[i]:
                i += 1

            protection = line[i].split("/")
            i += 1

            region_detail = None
            if len(line) >= i + 1:
                region_detail = line[i]

            result.append(
                Region(
                    region_type=region_type,
                    start=self.get_process_symbol(start),
                    end=end,
                    vsize=vsize,
                    protection=protection[0],
                    protection_max=protection[1],
                    region_detail=region_detail,
                )
            )

        return result

    @zyncio.zproperty
    async def regions(self) -> list[Region[DarwinSymbolT_co]]:
        """Return the list of VM regions for the process."""
        return await self.get_regions.z()

    @zyncio.zproperty
    async def cdhash(self) -> bytes:
        """Return the code directory hash for the process."""
        async with self._client.safe_malloc.z(CDHASH_SIZE) as cdhash:
            # by reversing online-auth-agent
            if await self._client.symbols.csops.z(self.pid, 5, cdhash, CDHASH_SIZE) != 0:
                raise BadReturnValueError(f"failed to get cdhash for {self.pid}")
            return await cdhash.peek.z(CDHASH_SIZE)

    def get_process_symbol(self, address: int) -> ProcessSymbol[DarwinSymbolT_co]:
        """Create a process symbol for the given address."""
        return ProcessSymbol(address, self)

    @zyncio.zmethod
    async def vm_allocate(self, size: int) -> ProcessSymbol[DarwinSymbolT_co]:
        """Allocate memory in the target task and return its address."""
        async with self._client.safe_malloc.z(8) as out_address:
            if await self._client.symbols.vm_allocate.z(
                await type(self).task(self), out_address, size, VM_FLAGS_ANYWHERE
            ):
                raise BadReturnValueError("vm_allocate() failed")
            return self.get_process_symbol(await out_address.getindex(0))

    @zyncio.zmethod
    async def dump_app(self, output_dir: str | PurePath, chunk_size: int = CHUNK_SIZE) -> None:
        """
        Based on:
        https://github.com/AloneMonkey/frida-ios-dump/blob/master/dump.js
        """
        for image in await type(self).app_images(self):
            relative_name = image.path.split(APP_SUFFIX, 1)[1]
            output_file = Path(output_dir).expanduser() / relative_name
            output_file.parent.mkdir(exist_ok=True, parents=True)
            logger.debug(f"dumping: {output_file}")

            with open(output_file, "wb") as output_file:
                macho_in_memory = mach_header_t.parse_stream(image.address)

                async with await self._client.fs.open.z(image.path, "r") as fat_file:
                    # locating the correct MachO offset within the FAT image (if FAT)
                    magic_in_fs = await fat_file.parse.z(Int32ul)
                    await fat_file.seek.z(0, SEEK_SET)
                    if magic_in_fs in (FAT_CIGAM, FAT_MAGIC):
                        parsed_fat = await fat_file.parse.z(fat_header)
                        for arch in parsed_fat.archs:
                            if (
                                arch.cputype == macho_in_memory.cputype
                                and arch.cpusubtype == macho_in_memory.cpusubtype
                            ):
                                # correct MachO offset found
                                file_offset = arch.offset
                                break
                        else:
                            raise RuntimeError("Failed to find file offset.")

                        await fat_file.seek.z(file_offset, SEEK_SET)

                    # perform actual MachO dump
                    output_file.seek(0, SEEK_SET)
                    while True:
                        chunk = await fat_file.read.z(chunk_size)
                        if len(chunk) == 0:
                            break
                        output_file.write(chunk)

                    offset_cryptid = None

                    # if image is encrypted, patch its encryption loader command
                    for load_command in macho_in_memory.load_commands:
                        if load_command.cmd in (
                            LOAD_COMMAND_TYPE.LC_ENCRYPTION_INFO_64,
                            LOAD_COMMAND_TYPE.LC_ENCRYPTION_INFO,
                        ):
                            offset_cryptid = load_command.data.cryptid_offset - image.address
                            crypt_offset = load_command.data.cryptoff
                            crypt_size = load_command.data.cryptsize
                            break
                    else:
                        raise RuntimeError("Failed to find LC_ENCRYPTION_INFO or LC_ENCRYPTION_INFO_64 command.")

                    if offset_cryptid is not None:
                        output_file.seek(offset_cryptid, SEEK_SET)
                        output_file.write(b"\x00" * 4)  # cryptid = 0
                        output_file.seek(crypt_offset, SEEK_SET)
                        output_file.flush()
                        output_file.write((image.address + crypt_offset).peek(crypt_size))

    @zyncio.zmethod
    async def get_mach_port_cross_ref_info(self) -> list[MachPortCrossRefInfo]:
        """Get all allocated mach ports and cross-refs to get the recv right owner"""
        own_ports: list[MachPortInfo] = []
        cross_refs_info: dict[int, list[MachPortInfo]] = {}
        async for port in self._client.processes.get_mach_ports.z():
            if port.pid == self.pid:
                own_ports.append(port)
            if port.ipc_object not in cross_refs_info:
                cross_refs_info[port.ipc_object] = []
            cross_refs_info[port.ipc_object].append(port)

        return [
            MachPortCrossRefInfo(
                name=port.name,
                ipc_object=port.ipc_object,
                recv_right_pid=cross_ref_port_info.pid,
                recv_right_proc_name=cross_ref_port_info.proc_name,
            )
            for port in own_ports
            for cross_ref_port_info in cross_refs_info[port.ipc_object]
            if cross_ref_port_info.has_recv_right
        ]

    @zyncio.zmethod
    async def get_memgraph_snapshot(self) -> bytes:
        """Return a memory graph snapshot as plist bytes."""
        scanner = None
        try:
            # first attempt via new API
            scanner = await (await self._client.symbols.objc_getClass.z("VMUProcessObjectGraph")).objc_call.z(
                "createWithTask:", await type(self).task_read(self)
            )
            snapshot_graph = await (await scanner.objc_call.z("plistRepresentationWithOptions:", 0)).py.z(bytes)
        except UnrecognizedSelectorError:
            # if failed, attempt with old API
            scanner = await (
                await (await self._client.symbols.objc_getClass.z("VMUTaskMemoryScanner")).objc_call.z("alloc")
            ).objc_call.z("initWithTask:", await type(self).task_read(self))
            await scanner.objc_call.z("addRootNodesFromTask")
            await scanner.objc_call.z("addMallocNodesFromTask")
            snapshot_graph = await (
                await (await scanner.objc_call.z("processSnapshotGraph")).objc_call.z(
                    "plistRepresentationWithOptions:", 0
                )
            ).py.z(bytes)
        finally:
            if scanner is not None:
                # free object scanner so process can resume
                await scanner.objc_call.z("release")
        return snapshot_graph

    def __repr__(self) -> str:
        """Return a debug representation of the process."""
        path = self.path if zyncio.is_sync(self) else getattr(self, "_path", "<not cached yet>")

        return f"<{self.__class__.__name__} PID:{self.pid} PATH:{path}>"


class DarwinProcesses(Processes["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """manage processes"""

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        """Initialize the Darwin process subsystem."""
        super().__init__(client)
        client.load_framework_lazy("Symbolication")

    _self_process: Process[DarwinSymbolT_co] | None = None

    @zyncio.zmethod
    async def get_self(self) -> Process[DarwinSymbolT_co]:
        """get self process"""
        if self._self_process is None:
            self._self_process = Process(self._client, await self._client.get_pid.z())

        return self._self_process

    @zyncio.zmethod
    async def get_by_pid(self, pid: int) -> Process[DarwinSymbolT_co]:
        """get process object by pid"""
        proc_list = await self.list.z()
        for p in proc_list:
            if p.pid == pid:
                return p
        raise ArgumentError(f"failed to locate process with pid: {pid}")

    @zyncio.zmethod
    async def get_by_basename(self, name: str) -> Process[DarwinSymbolT_co]:
        """get process object by basename"""
        proc_list = await self.list.z()
        for p in proc_list:
            if await type(p).basename(p) == name:
                return p
        raise ArgumentError(f"failed to locate process with name: {name}")

    @zyncio.zmethod
    async def get_by_name(self, name: str) -> Process[DarwinSymbolT_co]:
        """get process object by name"""
        proc_list = await self.list.z()
        for p in proc_list:
            if await type(p).name(p) == name:
                return p
        raise ArgumentError(f"failed to locate process with name: {name}")

    @zyncio.zmethod
    async def grep(self, name: str) -> list[Process[DarwinSymbolT_co]]:
        """get process list by basename filter"""
        result = []
        proc_list = await self.list.z()
        for p in proc_list:
            basename = await type(p).basename(p)
            if basename and name in basename:
                result.append(p)
        return result

    @zyncio.zmethod
    async def get_processes_by_listening_port(self, port: int) -> list[Process[DarwinSymbolT_co]]:
        """get a process object listening on the specified port"""
        listening_processes = []
        for process in await self.list.z():
            try:
                fds = await type(process).fds(process)
            except BadReturnValueError:
                # it's possible to get error if new processes have since died or the rpcserver
                # doesn't have the required permissions to access all the processes
                continue

            for fd in fds:
                if (isinstance(fd, (Ipv4SocketFd, Ipv6SocketFd))) and fd.local_port == port and fd.remote_port == 0:
                    listening_processes.append(process)
        return listening_processes

    @zyncio.zmethod
    async def lsof(self) -> dict[int, list[Fd]]:
        """get dictionary of pid to its opened fds"""
        result = {}
        for process in await self.list.z():
            try:
                fds = await type(process).fds(process)
            except BadReturnValueError:
                # it's possible to get error if new processes have since died or the rpcserver
                # doesn't have the required permissions to access all the processes
                continue

            result[process.pid] = fds
        return result

    @zyncio.zmethod
    async def fuser(self, path: str | PurePath) -> list[Process[DarwinSymbolT_co]]:
        """get a list of all processes have an open hande to the specified path"""
        result = []
        proc_list = await self.list.z()
        for process in proc_list:
            try:
                fds = await type(process).fds(process)
            except BadReturnValueError:
                # it's possible to get error if new processes have since died or the rpcserver
                # doesn't have the required permissions to access all the processes
                continue

            for fd in fds:
                if isinstance(fd, FileFd) and (str(Path(fd.path).absolute()) == str(Path(path).absolute())):
                    result.append(process)

        return result

    @zyncio.zmethod
    async def list(self) -> list[Process[DarwinSymbolT_co]]:
        """list all currently running processes"""
        n = await self._client.symbols.proc_listallpids.z(0, 0)
        pid_buf_size = pid_t.sizeof() * n
        async with self._client.safe_malloc.z(pid_buf_size) as pid_buf:
            pid_buf.item_size = pid_t.sizeof()
            n = await self._client.symbols.proc_listallpids.z(pid_buf, pid_buf_size)

            result = []
            for i in range(n):
                pid = int(await pid_buf.getindex(i))
                result.append(Process(self._client, pid))
            return result

    @zyncio.zmethod
    async def disable_watchdog(self) -> None:
        """Continuously kill watchdogd to keep it disabled."""
        while True:
            with contextlib.suppress(ArgumentError):
                await (await self.get_by_basename.z("watchdogd")).kill.z(SIGKILL)

            await zync_sleep(self._client.__zync_mode__, 1)

    @zyncio.zgeneratormethod
    async def get_mach_ports(self, include_thread_info: bool = False) -> AsyncGenerator[MachPortInfo]:
        """Enumerate all mach ports (heavily inspired by lsmp)"""
        thread_info = None
        mach_task_self = await self._client.symbols.mach_task_self.z()

        malloc = self._client.symbols.malloc.call
        p_psets = await self._client.symbols.malloc.z(8)
        p_pset_count = await malloc(8)
        p_pset_priv = await malloc(8)
        p_tasks = await malloc(8)
        p_task_count = await malloc(8)
        p_count = await malloc(4)
        ports_info = await malloc(4 * 2 * EXC_TYPES_COUNT)
        masks = await malloc(4 * EXC_TYPES_COUNT)
        behaviors = await malloc(4 * EXC_TYPES_COUNT)
        flavors = await malloc(4 * EXC_TYPES_COUNT)
        p_thread_count = await malloc(4)
        p_thread_ports = await malloc(8)
        info = await malloc(200)
        p_pid = await malloc(4)
        th_info = await malloc(thread_identifier_info.sizeof())
        p_th_kobject = await malloc(4)
        p_th_kotype = await malloc(4)
        p_th_info_count = await malloc(4)
        p_th_voucher = await self._client.symbols.calloc.z(4, 1)
        p_table = await malloc(8)
        unused = await malloc(200)
        proc_name = await malloc(100)
        p_kotype = await malloc(4)

        p_pid.item_size = 4
        p_count.item_size = 4
        p_thread_count.item_size = 4
        p_th_info_count.item_size = 4
        p_th_voucher.item_size = 4
        await p_th_info_count.setindex(0, THREAD_IDENTIFIER_INFO_COUNT)
        p_kotype.item_size = 4

        if await self._client.symbols.getuid.z() == 0:
            # if privileged, get the info for all tasks so we can match ports up
            if (
                await self._client.symbols.host_processor_sets.z(
                    await self._client.symbols.mach_host_self.z(),
                    p_psets,
                    p_pset_count,
                )
                != 0
            ):
                raise BadReturnValueError("host_processor_sets() failed")
            if await p_pset_count.getindex(0) != 1:
                raise BadReturnValueError("Assertion Failure: pset count greater than one")

            # convert the processor-set-name port to a privileged port
            if (
                await self._client.symbols.host_processor_set_priv.z(
                    await self._client.symbols.mach_host_self.z(),
                    await p_psets.getindex(0, 0),
                    p_pset_priv,
                )
                != 0
            ):
                raise BadReturnValueError("host_processor_set_priv() failed")

            await self._client.symbols.mach_port_deallocate.z(mach_task_self, await p_psets.getindex(0, 0))
            await self._client.symbols.vm_deallocate.z(
                mach_task_self,
                await p_psets.getindex(0),
                await p_pset_count.getindex(0) * mach_port_t.sizeof(),
            )

            # convert the processor-set-priv to a list of task read ports for the processor set
            if (
                await self._client.symbols.processor_set_tasks_with_flavor.z(
                    await p_pset_priv.getindex(0),
                    TASK_FLAVOR_READ,
                    p_tasks,
                    p_task_count,
                )
                != 0
            ):
                raise BadReturnValueError("processor_set_tasks_with_flavor() failed")

            await self._client.symbols.vm_deallocate.z(mach_task_self, await p_pset_priv.getindex(0))

            # swap my current instances port to be last to collect all threads and exception port info
            my_task_position = None
            task_count = await p_task_count.getindex(0)
            tasks = list(
                struct.unpack(f"<{int(task_count)}I", await (await p_tasks.getindex(0)).peek.z(task_count * 4))
            )

            for i in range(task_count):
                if await self._client.symbols.mach_task_is_self.z(tasks[i]):
                    my_task_position = i
                    break

            if my_task_position is not None:
                swap_holder = tasks[task_count - 1]
                tasks[task_count - 1] = tasks[my_task_position]
                tasks[my_task_position] = swap_holder
        else:
            logger.warning("should run as root for best output (cross-ref to other tasks' ports)")
            # just the one process
            task_count = 1
            async with self._client.safe_malloc.z(8) as p_task:
                ret = await self._client.symbols.task_read_for_pid.z(
                    mach_task_self,
                    (await self.get_self.z()).pid,
                    p_task,
                )
                if ret != 0:
                    raise BadReturnValueError("task_read_for_pid() failed")
                tasks = [await p_task.getindex(0)]

        for task in tasks:
            await self._client.symbols.pid_for_task.z(task, p_pid)
            pid = (await p_pid.getindex(0)).c_uint32

            if (
                await self._client.symbols.task_get_exception_ports_info.z(
                    task, EXC_MASK_ALL, masks, p_count, ports_info, behaviors, flavors
                )
                != 0
            ):
                raise BadReturnValueError("task_get_exception_ports_info() failed")

            if include_thread_info:
                # collect threads port as well
                if await self._client.symbols.task_threads.z(task, p_thread_ports, p_thread_count) != 0:
                    raise BadReturnValueError("task_threads() failed")

                # collect the thread information
                thread_count = (await p_thread_count.getindex(0)).c_uint32
                thread_ports = struct.unpack(
                    f"<{thread_count}I",
                    await (await p_thread_ports.getindex(0)).peek.z(4 * thread_count),
                )
                thread_ids = []
                for thread_port in thread_ports:
                    ret = await self._client.symbols.thread_get_exception_ports_info.z(
                        thread_port,
                        EXC_MASK_ALL,
                        masks,
                        p_count,
                        ports_info,
                        behaviors,
                        flavors,
                    )
                    if ret != 0:
                        raise BadReturnValueError(
                            f"thread_get_exception_ports_info() failed: "
                            f"{await (await self._client.symbols.mach_error_string.z(ret)).peek_str.z()}"
                        )

                    if (
                        await self._client.symbols.mach_port_kernel_object.z(
                            mach_task_self, thread_port, p_th_kotype, p_th_kobject
                        )
                        == 0
                    ) and (
                        await self._client.symbols.thread_info.z(
                            mach_task_self,
                            thread_port,
                            THREAD_IDENTIFIER_INFO,
                            th_info,
                            await p_th_info_count.getindex(0),
                        )
                        == 0
                    ):
                        thread_id = (await th_info.parse.z(thread_identifier_info)).thread_id
                        thread_ids.append(thread_id)

                    await self._client.symbols.mach_port_deallocate.z(mach_task_self, thread_port)
                thread_info = MachPortThreadInfo(thread_ids=thread_ids)

            if await self._client.symbols.mach_port_space_info.z(task, info, p_table, p_count, unused, unused) != 0:
                raise BadReturnValueError("mach_port_space_info() failed")

            proc_name_str = (
                await proc_name.peek_str.z()
                if await self._client.symbols.proc_name.z(pid, proc_name, 100) != 0
                else None
            )

            count = (await p_count.getindex(0)).c_uint32
            table_struct = Array(count, ipc_info_name_t)

            parsed_table = await (await p_table.getindex(0)).parse.z(table_struct)

            for entry in parsed_table:
                dnreq = False
                rights = []

                if entry.iin_type & MACH_PORT_TYPE_ALL_RIGHTS == 0:
                    # skip empty slots in the table
                    continue

                if entry.iin_type == MACH_PORT_TYPE_PORT_SET:
                    continue

                if entry.iin_type & MACH_PORT_TYPE_SEND:
                    rights.append("send")

                if entry.iin_type & MACH_PORT_TYPE_DNREQUEST:
                    dnreq = True

                if entry.iin_type & MACH_PORT_TYPE_RECEIVE:
                    rights.append("recv")

                elif entry.iin_type == MACH_PORT_TYPE_DEAD_NAME:
                    continue

                if entry.iin_type == MACH_PORT_TYPE_SEND_ONCE:
                    pass

                yield MachPortInfo(
                    task=task,
                    pid=pid,
                    name=entry.iin_name,
                    rights=rights,
                    ipc_object=entry.iin_object,
                    dead=dnreq,
                    proc_name=proc_name_str,
                    thread_info=thread_info,
                )
