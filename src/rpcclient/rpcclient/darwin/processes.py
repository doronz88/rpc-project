import dataclasses
import errno
import logging
import posixpath
import re
import struct
import time
from collections import namedtuple
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from cached_property import cached_property
from construct import Array, Container, Int32ul
from parameter_decorators import path_to_str

from rpcclient.darwin.consts import EXC_MASK_ALL, EXC_TYPES_COUNT, MACH_PORT_TYPE_ALL_RIGHTS, \
    MACH_PORT_TYPE_DEAD_NAME, MACH_PORT_TYPE_DNREQUEST, MACH_PORT_TYPE_PORT_SET, MACH_PORT_TYPE_RECEIVE, \
    MACH_PORT_TYPE_SEND, MACH_PORT_TYPE_SEND_ONCE, TASK_DYLD_INFO, TASK_FLAVOR_READ, THREAD_IDENTIFIER_INFO, \
    VM_FLAGS_ANYWHERE, ARMThreadFlavors, x86_THREAD_STATE64
from rpcclient.darwin.structs import ARM_THREAD_STATE64_COUNT, FAT_CIGAM, FAT_MAGIC, LOAD_COMMAND_TYPE, MAXPATHLEN, \
    PROC_PIDFDPIPEINFO, PROC_PIDFDSOCKETINFO, PROC_PIDFDVNODEPATHINFO, PROC_PIDLISTFDS, PROC_PIDTASKALLINFO, \
    PROX_FDTYPE_KQUEUE, PROX_FDTYPE_PIPE, PROX_FDTYPE_SOCKET, PROX_FDTYPE_VNODE, TASK_DYLD_INFO_COUNT, \
    THREAD_IDENTIFIER_INFO_COUNT, all_image_infos_t, arm_thread_state64_t, dyld_image_info_t, fat_header, \
    ipc_info_name_t, mach_header_t, mach_port_t, pid_t, pipe_info, proc_fdinfo, proc_taskallinfo, procargs2_t, \
    so_family_t, so_kind_t, socket_fdinfo, task_dyld_info_data_t, thread_identifier_info, vnode_fdinfowithpath, \
    x86_thread_state64_t
from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.exceptions import ArgumentError, BadReturnValueError, MissingLibraryError, ProcessSymbolAbsentError, \
    RpcClientException, SymbolAbsentError, UnrecognizedSelectorError
from rpcclient.processes import Processes
from rpcclient.protobuf_bridge import ARCH_ARM64
from rpcclient.structs.consts import RTLD_NOW, SEEK_SET, SIGKILL, SIGTERM
from rpcclient.symbol import ADDRESS_SIZE_TO_STRUCT_FORMAT, Symbol
from rpcclient.sysctl import CTL, KERN

_CF_STRING_ARRAY_PREFIX_LEN = len('    "')
_CF_STRING_ARRAY_SUFFIX_LEN = len('",')
_BACKTRACE_FRAME_REGEX = re.compile(r'\[\s*(\d+)\] (0x[0-9a-f]+)\s+\{(.+?) \+ (.+?)\} (.*)')

FdStruct = namedtuple('FdStruct', 'fd struct')

logger = logging.getLogger(__name__)

CDHASH_SIZE = 20
CHUNK_SIZE = 1024 * 64
APP_SUFFIX = '.app/'


@dataclasses.dataclass()
class Fd:
    fd: int


@dataclasses.dataclass()
class KQueueFd(Fd):
    pass


@dataclasses.dataclass()
class PipeFd(Fd):
    pass


@dataclasses.dataclass()
class FileFd(Fd):
    path: str


@dataclasses.dataclass()
class UnixFd(Fd):
    path: str


@dataclasses.dataclass()
class SocketFd(Fd):
    pass


@dataclasses.dataclass()
class Ipv4SocketFd(SocketFd):
    local_address: str
    local_port: int
    remote_address: str
    remote_port: int  # when remote 0, the socket is for listening


@dataclasses.dataclass()
class Ipv6SocketFd(SocketFd):
    local_address: str
    local_port: int
    remote_address: str
    remote_port: int  # when remote 0, the socket is for listening


@dataclasses.dataclass()
class Ipv4TcpFd(Ipv4SocketFd):
    pass


@dataclasses.dataclass()
class Ipv6TcpFd(Ipv6SocketFd):
    pass


@dataclasses.dataclass()
class Ipv4UdpFd(Ipv4SocketFd):
    pass


@dataclasses.dataclass()
class Ipv6UdpFd(Ipv6SocketFd):
    pass


Image = namedtuple('Image', 'address path')

SOCKET_TYPE_DATACLASS = {
    so_family_t.AF_INET: {
        so_kind_t.SOCKINFO_TCP: Ipv4TcpFd,
        so_kind_t.SOCKINFO_IN: Ipv4UdpFd,
    },
    so_family_t.AF_INET6: {
        so_kind_t.SOCKINFO_TCP: Ipv6TcpFd,
        so_kind_t.SOCKINFO_IN: Ipv6UdpFd,
    }
}


class Thread:
    def __init__(self, client, thread_id: int):
        self._client = client
        self._thread_id = thread_id

    @property
    def thread_id(self) -> int:
        return self._thread_id

    def get_state(self):
        raise NotImplementedError()

    def set_state(self, state: dict):
        raise NotImplementedError()

    def resume(self):
        raise NotImplementedError()

    def suspend(self):
        raise NotImplementedError()

    def __repr__(self):
        return f'<{self.__class__.__name__} TID:{self._thread_id}>'


class IntelThread64(Thread):
    def get_state(self):
        with self._client.safe_malloc(x86_thread_state64_t.sizeof()) as p_state:
            with self._client.safe_malloc(x86_thread_state64_t.sizeof()) as p_thread_state_count:
                p_thread_state_count[0] = x86_thread_state64_t.sizeof() // Int32ul.sizeof()
                if self._client.symbols.thread_get_state(self._thread_id, x86_THREAD_STATE64,
                                                         p_state, p_thread_state_count):
                    raise BadReturnValueError('thread_get_state() failed')
                return x86_thread_state64_t.parse_stream(p_state)

    def set_state(self, state: dict) -> None:
        if self._client.symbols.thread_set_state(self._thread_id, x86_THREAD_STATE64,
                                                 x86_thread_state64_t.build(state),
                                                 x86_thread_state64_t.sizeof() // Int32ul.sizeof()):
            raise BadReturnValueError('thread_set_state() failed')


class ArmThread64(Thread):
    def get_state(self):
        with self._client.safe_malloc(arm_thread_state64_t.sizeof()) as p_state:
            with self._client.safe_malloc(arm_thread_state64_t.sizeof()) as p_thread_state_count:
                p_thread_state_count[0] = ARM_THREAD_STATE64_COUNT
                if self._client.symbols.thread_get_state(self._thread_id, ARMThreadFlavors.ARM_THREAD_STATE64,
                                                         p_state, p_thread_state_count):
                    raise BadReturnValueError('thread_get_state() failed')
                return arm_thread_state64_t.parse_stream(p_state)

    def set_state(self, state: dict) -> None:
        if self._client.symbols.thread_set_state(self._thread_id, ARMThreadFlavors.ARM_THREAD_STATE64,
                                                 arm_thread_state64_t.build(state),
                                                 ARM_THREAD_STATE64_COUNT):
            raise BadReturnValueError('thread_set_state() failed')

    def suspend(self):
        if self._client.symbols.thread_suspend(self._thread_id):
            raise BadReturnValueError('thread_suspend() failed')

    def resume(self):
        if self._client.symbols.thread_resume(self._thread_id):
            raise BadReturnValueError('thread_resume() failed')


@dataclasses.dataclass
class Region:
    region_type: str
    start: 'ProcessSymbol'
    end: int
    vsize: str
    protection: str
    protection_max: str
    region_detail: str

    @property
    def size(self) -> int:
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
        return f'<{self.__class__.__name__} [{self.depth:3}] 0x{self.address:x} ({self.section} + 0x{self.offset:x}) ' \
               f'{self.symbol_name}>'


@dataclasses.dataclass
class Backtrace:
    flavor: str
    time_start: float
    time_end: float
    pid: int
    thread_id: int
    dispatch_queue_serial_num: int
    frames: list[Frame]

    def __init__(self, vmu_backtrace: DarwinSymbol):
        backtrace = vmu_backtrace.objc_call('description').py()
        match = re.match(r'VMUBacktrace \(Flavor: (?P<flavor>.+?) Simple Time: (?P<time>.+?) '
                         r'Process: (?P<pid>\d+) Thread: (?P<thread_id>.+?)  Dispatch queue serial num: '
                         r'(?P<dispatch_queue_serial_num>\d+)\)', backtrace)
        self.flavor = match.group('flavor')
        self.pid = int(match.group('pid'))
        self.thread_id = int(match.group('thread_id'), 16)
        self.dispatch_queue_serial_num = int(match.group('dispatch_queue_serial_num'))

        self.frames = []
        for frame in re.findall(_BACKTRACE_FRAME_REGEX, backtrace):
            self.frames.append(Frame(depth=int(frame[0]), address=int(frame[1], 0), section=frame[2],
                                     offset=int(frame[3], 0), symbol_name=frame[4]))

    def __repr__(self):
        buf = f'<{self.__class__.__name__} PID: {self.pid} TID: {self.thread_id}\n'
        for frame in self.frames:
            buf += f'    {frame}\n'
        buf += '>'
        return buf


class ProcessSymbol(Symbol):
    @classmethod
    def create(cls, value: int, client, process):
        symbol = super().create(value, client)
        symbol = ProcessSymbol(symbol)
        symbol._prepare(client)
        symbol.process = process
        return symbol

    def _clone_from_value(self, value: int):
        return self.create(value, self._client, self.process)

    def peek(self, count: int) -> bytes:
        return self.process.peek(self, count)

    def poke(self, buf: bytes) -> None:
        return self.process.poke(self, buf)

    def peek_str(self, encoding='utf-8') -> str:
        """ peek string at given address """
        return self.process.peek_str(self, encoding)

    @property
    def dl_info(self) -> Container:
        raise NotImplementedError('dl_info isn\'t implemented for remote process symbols')

    @property
    def name(self) -> str:
        return self.process.get_symbol_name(self)

    @property
    def filename(self) -> str:
        return self.process.get_symbol_image(self.name).path

    def __getitem__(self, item) -> 'ProcessSymbol':
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        addr = self + item * self.item_size
        deref = struct.unpack(self._client._endianness + fmt, self.process.peek(addr, self.item_size))[0]
        return self.create(deref, self._client, self.process)

    def __setitem__(self, item, value):
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        value = struct.pack(self._client._endianness + fmt, int(value))
        self.process.poke(self + item * self.item_size, value)

    def __call__(self, *args, **kwargs):
        raise RpcClientException('ProcessSymbol is not callable')


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
    proc_name: Optional[str] = None
    thread_info: Optional[MachPortThreadInfo] = None

    @property
    def has_recv_right(self) -> bool:
        return 'recv' in self.rights

    @property
    def has_send_right(self) -> bool:
        return 'send' in self.rights


@dataclasses.dataclass
class MachPortCrossRefInfo:
    name: int
    ipc_object: int
    recv_right_pid: int
    recv_right_proc_name: str


class Process:
    PEEK_STR_CHUNK_SIZE = 0x100

    def __init__(self, client, pid: int):
        self._client = client
        self._pid = pid

        if self._client.arch == ARCH_ARM64:
            self._thread_class = ArmThread64
        else:
            self._thread_class = IntelThread64

    def kill(self, sig: int = SIGTERM):
        """ kill(pid, sig) at remote. read man for more details. """
        return self._client.processes.kill(self._pid, sig)

    def waitpid(self, flags: int = 0):
        """ waitpid(pid, stat_loc, 0) at remote. read man for more details. """
        return self._client.processes.waitpid(self._pid, flags)

    def peek(self, address: int, size: int) -> bytes:
        """ peek at memory address """
        with self._client.safe_malloc(size) as buf:
            with self._client.safe_malloc(8) as p_size:
                p_size[0] = size
                if self._client.symbols.vm_read_overwrite(self.task, address, size, buf, p_size):
                    raise BadReturnValueError('vm_read() failed')
                return buf.peek(size)

    def peek_str(self, address: int, encoding='utf-8') -> str:
        """ peek string at memory address """
        size = self.PEEK_STR_CHUNK_SIZE
        buf = b''

        while size:
            try:
                buf += self.peek(address, size)
                if b'\x00' in buf:
                    return buf.split(b'\x00', 1)[0].decode(encoding)
                address += size
            except BadReturnValueError:
                size = size // 2

    def poke(self, address: int, buf: bytes):
        """ poke at memory address """
        if self._client.symbols.vm_write(self.task, address, buf, len(buf)):
            raise BadReturnValueError('vm_write() failed')

    def get_symbol_name(self, address: int) -> str:
        if self._client.arch != ARCH_ARM64:
            raise NotImplementedError('implemented only on ARCH_ARM64')
        result = self.vmu_object_identifier.objc_call('symbolForAddress:', address, return_raw=True)
        if result.x0 == 0 and result.x1 == 0:
            raise SymbolAbsentError()
        return self._client.symbols.CSSymbolGetName(result.x0, result.x1).peek_str()

    def get_symbol_image(self, name: str) -> Image:
        for image in self.images:
            result = self.get_symbol_address(name, posixpath.basename(image.path))
            if result:
                return image

        raise ProcessSymbolAbsentError()

    def get_symbol_class_info(self, address: int) -> DarwinSymbol:
        return self.vmu_object_identifier.objc_call('classInfoForMemory:length:', address, 8)

    def get_symbol_address(self, name: str, lib: str = None) -> Union[DarwinSymbol, ProcessSymbol]:
        if lib is not None:
            address = self.vmu_object_identifier.objc_call('addressOfSymbol:inLibrary:', name, lib).c_uint64
            if self.pid == self._client.pid:
                return self._client.symbol(address)
            return ProcessSymbol.create(address, self._client, self)

        image = self.get_symbol_image(name)
        return self.get_symbol_address(name, posixpath.basename(image.path))

    @property
    def loaded_classes(self):
        realized_classes = self.vmu_object_identifier.objc_call('realizedClasses')

        for i in range(1, realized_classes.objc_call('count') + 1):
            class_info = realized_classes.objc_call('classInfoForIndex:', i)
            name = class_info.objc_call('className').py()
            type_name = class_info.objc_call('typeName').py()
            binary_path = class_info.objc_call('binaryPath').py()
            yield LoadedClass(name=name, type_name=type_name, binary_path=binary_path)

    @property
    def images(self) -> list[Image]:
        """ get loaded image list """
        result = []

        with self._client.safe_malloc(task_dyld_info_data_t.sizeof()) as dyld_info:
            with self._client.safe_calloc(8) as count:
                count[0] = TASK_DYLD_INFO_COUNT
                if self._client.symbols.task_info(self.task, TASK_DYLD_INFO, dyld_info, count):
                    raise BadReturnValueError('task_info(TASK_DYLD_INFO) failed')
                dyld_info_data = task_dyld_info_data_t.parse_stream(dyld_info)
        all_image_infos = all_image_infos_t.parse(
            self.peek(dyld_info_data.all_image_info_addr, dyld_info_data.all_image_info_size))

        buf = self.peek(all_image_infos.infoArray, all_image_infos.infoArrayCount * dyld_image_info_t.sizeof())
        for image in Array(all_image_infos.infoArrayCount, dyld_image_info_t).parse(buf):
            path = self.peek_str(image.imageFilePath)
            result.append(Image(address=self.get_process_symbol(image.imageLoadAddress), path=path))
        return result

    @property
    def app_images(self) -> list[Image]:
        return [image for image in self.images if APP_SUFFIX in image.path]

    @property
    def threads(self) -> list[Thread]:
        result = []
        with self._client.safe_malloc(8) as threads:
            with self._client.safe_malloc(4) as count:
                count.item_size = 4
                if self._client.symbols.task_threads(self.task, threads, count):
                    raise BadReturnValueError('task_threads() failed')

                for tid in Array(count[0].c_uint32, Int32ul).parse(threads[0].peek(count[0] * 4)):
                    result.append(self._thread_class(self._client, tid))
        return result

    @property
    def pid(self) -> int:
        """ get pid """
        return self._pid

    @property
    def fds(self) -> list[Fd]:
        """ get a list of process opened file descriptors """
        result = []
        for fdstruct in self.fd_structs:
            fd = fdstruct.fd
            parsed = fdstruct.struct

            if fd.proc_fdtype == PROX_FDTYPE_VNODE:
                result.append(FileFd(fd=fd.proc_fd, path=parsed.pvip.vip_path))

            elif fd.proc_fdtype == PROX_FDTYPE_KQUEUE:
                result.append(KQueueFd(fd=fd.proc_fd))

            elif fd.proc_fdtype == PROX_FDTYPE_PIPE:
                result.append(PipeFd(fd=fd.proc_fd))

            elif fd.proc_fdtype == PROX_FDTYPE_SOCKET:
                if parsed.psi.soi_kind in (so_kind_t.SOCKINFO_TCP, so_kind_t.SOCKINFO_IN):
                    correct_class = SOCKET_TYPE_DATACLASS[parsed.psi.soi_family][parsed.psi.soi_kind]

                    if parsed.psi.soi_kind == so_kind_t.SOCKINFO_TCP:
                        info = parsed.psi.soi_proto.pri_tcp.tcpsi_ini
                    else:
                        info = parsed.psi.soi_proto.pri_in
                    result.append(correct_class(fd=fd.proc_fd,
                                                local_address=info.insi_laddr.ina_46.i46a_addr4,
                                                local_port=info.insi_lport,
                                                remote_address=info.insi_faddr.ina_46.i46a_addr4,
                                                remote_port=info.insi_fport))

                elif parsed.psi.soi_kind == so_kind_t.SOCKINFO_UN:
                    result.append(UnixFd(fd=fd.proc_fd, path=parsed.psi.soi_proto.pri_un.unsi_addr.ua_sun.sun_path))

        return result

    @property
    def fd_structs(self) -> list[FdStruct]:
        """ get a list of process opened file descriptors as raw structs """
        result = []
        size = self._client.symbols.proc_pidinfo(self.pid, PROC_PIDLISTFDS, 0, 0, 0)

        vi_size = 8196  # should be enough for all structs
        with self._client.safe_malloc(vi_size) as vi_buf:
            with self._client.safe_malloc(size) as fdinfo_buf:
                size = int(self._client.symbols.proc_pidinfo(self.pid, PROC_PIDLISTFDS, 0, fdinfo_buf, size))
                if not size:
                    raise BadReturnValueError('proc_pidinfo(PROC_PIDLISTFDS) failed')

                for fd in Array(size // proc_fdinfo.sizeof(), proc_fdinfo).parse(fdinfo_buf.peek(size)):

                    if fd.proc_fdtype == PROX_FDTYPE_VNODE:
                        # file
                        vs = self._client.symbols.proc_pidfdinfo(self.pid, fd.proc_fd, PROC_PIDFDVNODEPATHINFO, vi_buf,
                                                                 vi_size)
                        if not vs:
                            if self._client.errno == errno.EBADF:
                                # lsof treats this as fine
                                continue
                            raise BadReturnValueError(
                                f'proc_pidinfo(PROC_PIDFDVNODEPATHINFO) failed for fd: {fd.proc_fd} '
                                f'({self._client.last_error})')

                        result.append(
                            FdStruct(fd=fd,
                                     struct=vnode_fdinfowithpath.parse(vi_buf.peek(vnode_fdinfowithpath.sizeof()))))

                    elif fd.proc_fdtype == PROX_FDTYPE_KQUEUE:
                        result.append(FdStruct(fd=fd, struct=None))

                    elif fd.proc_fdtype == PROX_FDTYPE_SOCKET:
                        # socket
                        vs = self._client.symbols.proc_pidfdinfo(self.pid, fd.proc_fd, PROC_PIDFDSOCKETINFO, vi_buf,
                                                                 vi_size)
                        if not vs:
                            if self._client.errno == errno.EBADF:
                                # lsof treats this as fine
                                continue
                            raise BadReturnValueError(
                                f'proc_pidinfo(PROC_PIDFDSOCKETINFO) failed ({self._client.last_error})')

                        result.append(FdStruct(fd=fd, struct=socket_fdinfo.parse(vi_buf.peek(vi_size))))

                    elif fd.proc_fdtype == PROX_FDTYPE_PIPE:
                        # pipe
                        vs = self._client.symbols.proc_pidfdinfo(self.pid, fd.proc_fd, PROC_PIDFDPIPEINFO, vi_buf,
                                                                 vi_size)
                        if not vs:
                            if self._client.errno == errno.EBADF:
                                # lsof treats this as fine
                                continue
                            raise BadReturnValueError(
                                f'proc_pidinfo(PROC_PIDFDPIPEINFO) failed ({self._client.last_error})')

                        result.append(
                            FdStruct(fd=fd,
                                     struct=pipe_info.parse(vi_buf.peek(pipe_info.sizeof()))))

            return result

    @property
    def task_all_info(self):
        """ get a list of process opened file descriptors """
        with self._client.safe_malloc(proc_taskallinfo.sizeof()) as pti:
            if not self._client.symbols.proc_pidinfo(self.pid, PROC_PIDTASKALLINFO, 0, pti, proc_taskallinfo.sizeof()):
                raise BadReturnValueError('proc_pidinfo(PROC_PIDTASKALLINFO) failed')
            return proc_taskallinfo.parse_stream(pti)

    @property
    def backtraces(self) -> list[Backtrace]:
        result = []
        backtraces = self._client.symbols.objc_getClass('VMUSampler').objc_call('sampleAllThreadsOfTask:', self.task)
        for i in range(backtraces.objc_call('count')):
            bt = backtraces.objc_call('objectAtIndex:', i)
            result.append(Backtrace(bt))
        return result

    @cached_property
    def vmu_proc_info(self) -> DarwinSymbol:
        return self._client.symbols.objc_getClass('VMUProcInfo').objc_call('alloc').objc_call('initWithTask:',
                                                                                              self.task)

    @cached_property
    def vmu_region_identifier(self) -> DarwinSymbol:
        return self._client.symbols.objc_getClass('VMUVMRegionIdentifier').objc_call('alloc').objc_call('initWithTask:',
                                                                                                        self.task)

    @cached_property
    def vmu_object_identifier(self) -> DarwinSymbol:
        return self._client.symbols.objc_getClass('VMUObjectIdentifier').objc_call('alloc').objc_call('initWithTask:',
                                                                                                      self.task)

    @cached_property
    def task(self) -> int:
        self_task_port = self._client.symbols.mach_task_self()

        if self.pid == self._client.pid:
            return self_task_port

        with self._client.safe_malloc(8) as p_task:
            if self._client.symbols.task_for_pid(self_task_port, self.pid, p_task):
                raise BadReturnValueError('task_for_pid() failed')
            return p_task[0].c_int64

    @cached_property
    def path(self) -> Optional[str]:
        """ call proc_pidpath(filename, ...) at remote. review xnu header for more details. """
        with self._client.safe_malloc(MAXPATHLEN) as path:
            path_len = self._client.symbols.proc_pidpath(self.pid, path, MAXPATHLEN)
            if not path_len:
                return None
            return path.peek(path_len).decode()

    @cached_property
    def basename(self) -> Optional[str]:
        path = self.path
        if not path:
            return None
        return Path(path).parts[-1]

    @cached_property
    def name(self) -> str:
        return self.task_all_info.pbsd.pbi_name

    @cached_property
    def ppid(self) -> int:
        return self.task_all_info.pbsd.pbi_ppid

    @cached_property
    def uid(self) -> int:
        return self.task_all_info.pbsd.pbi_uid

    @cached_property
    def gid(self) -> int:
        return self.task_all_info.pbsd.pbi_gid

    @cached_property
    def ruid(self) -> int:
        return self.task_all_info.pbsd.pbi_ruid

    @cached_property
    def rgid(self) -> int:
        return self.task_all_info.pbsd.pbi_rgid

    @cached_property
    def start_time(self) -> datetime:
        if self._client.arch != ARCH_ARM64:
            raise NotImplementedError('implemented only on ARCH_ARM64')
        val = self.vmu_proc_info.objc_call('startTime', return_raw=True)
        tv_sec = val.x0
        tv_nsec = val.x1
        return datetime.fromtimestamp(tv_sec + (tv_nsec / (10 ** 9)))

    @property
    def parent(self) -> 'Process':
        return Process(self._client, self.ppid)

    @property
    def environ(self) -> list[str]:
        return self.vmu_proc_info.objc_call('envVars').py()

    @property
    def arguments(self) -> list[str]:
        return self.vmu_proc_info.objc_call('arguments').py()

    @property
    def raw_procargs2(self) -> bytes:
        return self._client.sysctl.get(CTL.KERN, KERN.PROCARGS2, self.pid)

    @property
    def procargs2(self) -> Container:
        return procargs2_t.parse(self.raw_procargs2)

    @property
    def regions(self) -> list[Region]:
        result = []

        # remove the '()' wrapping the list:
        #   (
        #       "item1",
        #       "item2",
        #   )
        buf = self.vmu_region_identifier.objc_call('regions').cfdesc.split('\n')[1:-1]

        for line in buf:
            # remove line prefix and suffix and split into words
            line = line[_CF_STRING_ARRAY_PREFIX_LEN:-_CF_STRING_ARRAY_SUFFIX_LEN].split()
            i = 0

            region_type = line[i]
            i += 1

            while '-' not in line[i]:
                # skip till address range
                i += 1

            address_range = line[i]
            i += 1
            start, end = address_range.split('-')
            start = int(start, 16)
            end = int(end, 16)
            vsize = None
            if 'V=' in line[i]:
                vsize = line[i].split('V=', 1)[1].split(']', 1)[0]

            while '/' not in line[i]:
                i += 1

            protection = line[i].split('/')
            i += 1

            region_detail = None
            if len(line) >= i + 1:
                region_detail = line[i]

            result.append(Region(region_type=region_type, start=self.get_process_symbol(start), end=end, vsize=vsize,
                                 protection=protection[0], protection_max=protection[1], region_detail=region_detail))

        return result

    @property
    def cdhash(self) -> bytes:
        with self._client.safe_malloc(CDHASH_SIZE) as cdhash:
            # by reversing online-auth-agent
            if 0 != self._client.symbols.csops(self.pid, 5, cdhash, CDHASH_SIZE):
                raise BadReturnValueError(f'failed to get cdhash for {self.pid}')
            return cdhash.peek(CDHASH_SIZE)

    def get_process_symbol(self, address: int) -> ProcessSymbol:
        return ProcessSymbol.create(address, self._client, self)

    def vm_allocate(self, size: int) -> ProcessSymbol:
        with self._client.safe_malloc(8) as out_address:
            if self._client.symbols.vm_allocate(self.task, out_address, size, VM_FLAGS_ANYWHERE):
                raise BadReturnValueError('vm_allocate() failed')
            return self.get_process_symbol(out_address[0])

    @path_to_str('output_dir')
    def dump_app(self, output_dir: str, chunk_size=CHUNK_SIZE) -> None:
        """
        Based on:
        https://github.com/AloneMonkey/frida-ios-dump/blob/master/dump.js
        """
        for image in self.app_images:
            relative_name = image.path.split(APP_SUFFIX, 1)[1]
            output_file = Path(output_dir).expanduser() / relative_name
            output_file.parent.mkdir(exist_ok=True, parents=True)
            logger.debug(f'dumping: {output_file}')

            with open(output_file, 'wb') as output_file:
                macho_in_memory = mach_header_t.parse_stream(image.address)

                with self._client.fs.open(image.path, 'r') as fat_file:
                    # locating the correct MachO offset within the FAT image (if FAT)
                    magic_in_fs = Int32ul.parse_stream(fat_file)
                    fat_file.seek(0, SEEK_SET)
                    if magic_in_fs in (FAT_CIGAM, FAT_MAGIC):
                        parsed_fat = fat_header.parse_stream(fat_file)
                        for arch in parsed_fat.archs:
                            if arch.cputype == macho_in_memory.cputype and arch.cpusubtype == macho_in_memory.cpusubtype:
                                # correct MachO offset found
                                file_offset = arch.offset
                                break
                        fat_file.seek(file_offset, SEEK_SET)

                    # perform actual MachO dump
                    output_file.seek(0, SEEK_SET)
                    while True:
                        chunk = fat_file.read(chunk_size)
                        if len(chunk) == 0:
                            break
                        output_file.write(chunk)

                    offset_cryptid = None

                    # if image is encrypted, patch its encryption loader command
                    for load_command in macho_in_memory.load_commands:
                        if load_command.cmd in (LOAD_COMMAND_TYPE.LC_ENCRYPTION_INFO_64,
                                                LOAD_COMMAND_TYPE.LC_ENCRYPTION_INFO):
                            offset_cryptid = load_command.data.cryptid_offset - image.address
                            crypt_offset = load_command.data.cryptoff
                            crypt_size = load_command.data.cryptsize
                            break

                    if offset_cryptid is not None:
                        output_file.seek(offset_cryptid, SEEK_SET)
                        output_file.write(b'\x00' * 4)  # cryptid = 0
                        output_file.seek(crypt_offset, SEEK_SET)
                        output_file.flush()
                        output_file.write((image.address + crypt_offset).peek(crypt_size))

    def get_mach_port_cross_ref_info(self) -> list[MachPortCrossRefInfo]:
        """ Get all allocated mach ports and cross-refs to get the recv right owner """
        result = []
        own_ports = []
        cross_refs_info = {}
        for port in self._client.processes.get_mach_ports():
            if port.pid == self.pid:
                own_ports.append(port)
            if port.ipc_object not in cross_refs_info:
                cross_refs_info[port.ipc_object] = []
            cross_refs_info[port.ipc_object].append(port)

        for port in own_ports:
            for cross_ref_port_info in cross_refs_info[port.ipc_object]:
                if cross_ref_port_info.has_recv_right:
                    result.append(MachPortCrossRefInfo(name=port.name, ipc_object=port.ipc_object,
                                                       recv_right_pid=cross_ref_port_info.pid,
                                                       recv_right_proc_name=cross_ref_port_info.proc_name))
        return result

    def get_memgraph_snapshot(self) -> bytes:
        scanner = None
        try:
            # first attempt via new API
            scanner = self._client.symbols.objc_getClass('VMUProcessObjectGraph').objc_call(
                'createWithTask:', self.task)
            snapshot_graph = scanner.objc_call('plistRepresentationWithOptions:', 0).py()
        except UnrecognizedSelectorError:
            # if failed, attempt with old API
            scanner = self._client.symbols.objc_getClass('VMUTaskMemoryScanner').objc_call('alloc').objc_call(
                'initWithTask:', self.task)
            scanner.objc_call('addRootNodesFromTask')
            scanner.objc_call('addMallocNodesFromTask')
            snapshot_graph = scanner.objc_call('processSnapshotGraph').objc_call(
                'plistRepresentationWithOptions:', 0).py()
        finally:
            if scanner is not None:
                # free object scanner so process can resume
                scanner.objc_call('release')
        return snapshot_graph

    def __repr__(self):
        return f'<{self.__class__.__name__} PID:{self.pid} PATH:{self.path}>'


class DarwinProcesses(Processes):
    """ manage processes """

    def __init__(self, client):
        super().__init__(client)
        self._load_symbolication_library()
        self._self_process = Process(self._client, self._client.pid)

    def _load_symbolication_library(self):
        options = [
            '/System/Library/PrivateFrameworks/Symbolication.framework/Symbolication'
        ]
        for option in options:
            if self._client.dlopen(option, RTLD_NOW):
                return
        raise MissingLibraryError('Symbolication library isn\'t available')

    def get_self(self) -> Process:
        """ get self process """
        return self._self_process

    def get_by_pid(self, pid: int) -> Process:
        """ get process object by pid """
        proc_list = self.list()
        for p in proc_list:
            if p.pid == pid:
                return p
        raise ArgumentError(f'failed to locate process with pid: {pid}')

    def get_by_basename(self, name: str) -> Process:
        """ get process object by basename """
        proc_list = self.list()
        for p in proc_list:
            if p.basename == name:
                return p
        raise ArgumentError(f'failed to locate process with name: {name}')

    def get_by_name(self, name: str) -> Process:
        """ get process object by name """
        proc_list = self.list()
        for p in proc_list:
            if p.name == name:
                return p
        raise ArgumentError(f'failed to locate process with name: {name}')

    def grep(self, name: str) -> list[Process]:
        """ get process list by basename filter """
        result = []
        proc_list = self.list()
        for p in proc_list:
            if p.basename and name in p.basename:
                result.append(p)
        return result

    def get_processes_by_listening_port(self, port: int) -> list[Process]:
        """ get a process object listening on the specified port """
        listening_processes = []
        for process in self.list():
            try:
                fds = process.fds
            except BadReturnValueError:
                # it's possible to get error if new processes have since died or the rpcserver
                # doesn't have the required permissions to access all the processes
                continue

            for fd in fds:
                if (isinstance(fd, Ipv4SocketFd) or isinstance(fd, Ipv6SocketFd)) and \
                        fd.local_port == port and fd.remote_port == 0:
                    listening_processes.append(process)
        return listening_processes

    def lsof(self) -> dict[int, list[Fd]]:
        """ get dictionary of pid to its opened fds """
        result = {}
        for process in self.list():
            try:
                fds = process.fds
            except BadReturnValueError:
                # it's possible to get error if new processes have since died or the rpcserver
                # doesn't have the required permissions to access all the processes
                continue

            result[process.pid] = fds
        return result

    @path_to_str('path')
    def fuser(self, path: str) -> list[Process]:
        """get a list of all processes have an open hande to the specified path """
        result = []
        proc_list = self.list()
        for process in proc_list:
            try:
                fds = process.fds
            except BadReturnValueError:
                # it's possible to get error if new processes have since died or the rpcserver
                # doesn't have the required permissions to access all the processes
                continue

            for fd in fds:
                if isinstance(fd, FileFd):
                    if str(Path(fd.path).absolute()) == str(Path(path).absolute()):
                        result.append(process)

        return result

    def list(self) -> list[Process]:
        """ list all currently running processes """
        n = self._client.symbols.proc_listallpids(0, 0)
        pid_buf_size = pid_t.sizeof() * n
        with self._client.safe_malloc(pid_buf_size) as pid_buf:
            pid_buf.item_size = pid_t.sizeof()
            n = self._client.symbols.proc_listallpids(pid_buf, pid_buf_size)

            result = []
            for i in range(n):
                pid = int(pid_buf[i])
                result.append(Process(self._client, pid))
            return result

    def disable_watchdog(self) -> None:
        while True:
            try:
                self.get_by_basename('watchdogd').kill(SIGKILL)
            except ArgumentError:
                pass
            time.sleep(1)

    def get_mach_ports(self, include_thread_info: bool = False) -> Generator[MachPortInfo, None, None]:  # noqa: C901
        """ Enumerate all mach ports (heavily inspired by lsmp) """
        thread_info = None
        mach_task_self = self._client.symbols.mach_task_self()

        p_psets = self._client.symbols.malloc(8)
        p_pset_count = self._client.symbols.malloc(8)
        p_pset_priv = self._client.symbols.malloc(8)
        p_tasks = self._client.symbols.malloc(8)
        p_task_count = self._client.symbols.malloc(8)
        p_count = self._client.symbols.malloc(4)
        ports_info = self._client.symbols.malloc(4 * 2 * EXC_TYPES_COUNT)
        masks = self._client.symbols.malloc(4 * EXC_TYPES_COUNT)
        behaviors = self._client.symbols.malloc(4 * EXC_TYPES_COUNT)
        flavors = self._client.symbols.malloc(4 * EXC_TYPES_COUNT)
        p_thread_count = self._client.symbols.malloc(4)
        p_thread_ports = self._client.symbols.malloc(8)
        info = self._client.symbols.malloc(200)
        p_pid = self._client.symbols.malloc(4)
        th_info = self._client.symbols.malloc(thread_identifier_info.sizeof())
        p_th_kobject = self._client.symbols.malloc(4)
        p_th_kotype = self._client.symbols.malloc(4)
        p_th_info_count = self._client.symbols.malloc(4)
        p_th_voucher = self._client.symbols.calloc(4, 1)
        p_table = self._client.symbols.malloc(8)
        unused = self._client.symbols.malloc(200)
        proc_name = self._client.symbols.malloc(100)
        p_kotype = self._client.symbols.malloc(4)

        p_pid.item_size = 4
        p_count.item_size = 4
        p_thread_count.item_size = 4
        p_th_info_count.item_size = 4
        p_th_voucher.item_size = 4
        p_th_info_count[0] = THREAD_IDENTIFIER_INFO_COUNT
        p_kotype.item_size = 4

        if self._client.symbols.getuid() == 0:
            # if privileged, get the info for all tasks so we can match ports up
            if self._client.symbols.host_processor_sets(self._client.symbols.mach_host_self(), p_psets,
                                                        p_pset_count) != 0:
                raise BadReturnValueError('host_processor_sets() failed')
            if p_pset_count[0] != 1:
                raise BadReturnValueError('Assertion Failure: pset count greater than one')

            # convert the processor-set-name port to a privileged port
            if self._client.symbols.host_processor_set_priv(self._client.symbols.mach_host_self(), p_psets[0][0],
                                                            p_pset_priv) != 0:
                raise BadReturnValueError('host_processor_set_priv() failed')

            self._client.symbols.mach_port_deallocate(mach_task_self, p_psets[0][0])
            self._client.symbols.vm_deallocate(mach_task_self, p_psets[0], p_pset_count[0] * mach_port_t.sizeof())

            # convert the processor-set-priv to a list of task read ports for the processor set
            if self._client.symbols.processor_set_tasks_with_flavor(p_pset_priv[0], TASK_FLAVOR_READ, p_tasks,
                                                                    p_task_count) != 0:
                raise BadReturnValueError('processor_set_tasks_with_flavor() failed')

            self._client.symbols.vm_deallocate(mach_task_self, p_pset_priv[0])

            # swap my current instances port to be last to collect all threads and exception port info
            my_task_position = None
            task_count = p_task_count[0]
            tasks = list(struct.unpack(f'<{int(task_count)}I', p_tasks[0].peek(task_count * 4)))

            for i in range(task_count):
                if self._client.symbols.mach_task_is_self(tasks[i]):
                    my_task_position = i
                    break
            if my_task_position is not None:
                swap_holder = tasks[task_count - 1]
                tasks[task_count - 1] = tasks[my_task_position]
                tasks[my_task_position] = swap_holder
        else:
            logger.warning('should run as root for best output (cross-ref to other tasks\' ports)')
            # just the one process
            task_count = 1
            with self._client.safe_malloc(8) as p_task:
                ret = self._client.symbols.task_read_for_pid(mach_task_self, self.pid, p_task)
                if ret != 0:
                    raise BadReturnValueError('task_read_for_pid() failed')
                tasks = [p_task[0]]

        for task in tasks:
            self._client.symbols.pid_for_task(task, p_pid)
            pid = p_pid[0].c_uint32

            if self._client.symbols.task_get_exception_ports_info(task, EXC_MASK_ALL, masks, p_count, ports_info,
                                                                  behaviors, flavors) != 0:
                raise BadReturnValueError('task_get_exception_ports_info() failed')

            if include_thread_info:
                # collect threads port as well
                if 0 != self._client.symbols.task_threads(task, p_thread_ports, p_thread_count):
                    raise BadReturnValueError('task_threads() failed')

                # collect the thread information
                thread_count = p_thread_count[0].c_uint32
                thread_ports = struct.unpack(f'<{thread_count}I', p_thread_ports[0].peek(4 * thread_count))
                thread_ids = []
                for thread_port in thread_ports:
                    ret = self._client.symbols.thread_get_exception_ports_info(
                        thread_port, EXC_MASK_ALL, masks, p_count, ports_info, behaviors, flavors)
                    if 0 != ret:
                        raise BadReturnValueError(
                            f'thread_get_exception_ports_info() failed: '
                            f'{self._client.symbols.mach_error_string(ret).peek_str()}')

                    if 0 == self._client.symbols.mach_port_kernel_object(mach_task_self, thread_port, p_th_kotype,
                                                                         p_th_kobject):
                        if 0 == self._client.symbols.thread_info(mach_task_self, thread_port,
                                                                 THREAD_IDENTIFIER_INFO, th_info, p_th_info_count[0]):
                            thread_id = thread_identifier_info.parse(
                                th_info.peek(thread_identifier_info.sizeof())).thread_id
                            thread_ids.append(thread_id)

                    self._client.symbols.mach_port_deallocate(mach_task_self, thread_port)
                thread_info = MachPortThreadInfo(thread_ids=thread_ids)

            if 0 != self._client.symbols.mach_port_space_info(task, info, p_table, p_count, unused, unused):
                raise BadReturnValueError('mach_port_space_info() failed')

            if 0 != self._client.symbols.proc_name(pid, proc_name, 100):
                proc_name_str = proc_name.peek_str()
            else:
                proc_name_str = None

            count = p_count[0].c_uint32
            table_struct = Array(count, ipc_info_name_t)

            parsed_table = table_struct.parse(p_table[0].peek(table_struct.sizeof()))

            for entry in parsed_table:
                dnreq = False
                rights = []

                if entry.iin_type & MACH_PORT_TYPE_ALL_RIGHTS == 0:
                    # skip empty slots in the table
                    continue

                if entry.iin_type == MACH_PORT_TYPE_PORT_SET:
                    continue

                if entry.iin_type & MACH_PORT_TYPE_SEND:
                    rights.append('send')

                if entry.iin_type & MACH_PORT_TYPE_DNREQUEST:
                    dnreq = True

                if entry.iin_type & MACH_PORT_TYPE_RECEIVE:
                    rights.append('recv')

                elif entry.iin_type == MACH_PORT_TYPE_DEAD_NAME:
                    continue

                if entry.iin_type == MACH_PORT_TYPE_SEND_ONCE:
                    pass

                yield MachPortInfo(
                    task=task, pid=pid, name=entry.iin_name, rights=rights, ipc_object=entry.iin_object, dead=dnreq,
                    proc_name=proc_name_str, thread_info=thread_info)
