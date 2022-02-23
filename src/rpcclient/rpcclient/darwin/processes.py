import dataclasses
import errno
from collections import namedtuple
from pathlib import Path
from typing import Optional, List, Mapping

from cached_property import cached_property
from construct import Array

from rpcclient.common import path_to_str
from rpcclient.exceptions import BadReturnValueError, ArgumentError
from rpcclient.processes import Processes
from rpcclient.darwin.structs import pid_t, MAXPATHLEN, PROC_PIDLISTFDS, proc_fdinfo, PROX_FDTYPE_VNODE, \
    vnode_fdinfowithpath, PROC_PIDFDVNODEPATHINFO, proc_taskallinfo, PROC_PIDTASKALLINFO, PROX_FDTYPE_SOCKET, \
    PROC_PIDFDSOCKETINFO, socket_fdinfo, so_kind_t, so_family_t, PROX_FDTYPE_PIPE, PROC_PIDFDPIPEINFO, pipe_info

FdStruct = namedtuple('FdStruct', 'fd struct')


@dataclasses.dataclass()
class Fd:
    fd: int


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


class Process:
    def __init__(self, client, pid: int):
        self._client = client
        self.pid = pid

    @cached_property
    def path(self) -> Optional[str]:
        """ call proc_pidpath(filename, ...) at remote. review xnu header for more details. """
        with self._client.safe_malloc(MAXPATHLEN) as path:
            path_len = self._client.symbols.proc_pidpath(self.pid, path, MAXPATHLEN)
            if not path_len:
                return None
            return path.peek(path_len).decode()

    @property
    def fds(self) -> List[Fd]:
        """ get a list of process opened file descriptors """
        result = []
        for fdstruct in self.fd_structs:
            fd = fdstruct.fd
            parsed = fdstruct.struct

            if fd.proc_fdtype == PROX_FDTYPE_VNODE:
                result.append(FileFd(fd=fd.proc_fd, path=parsed.pvip.vip_path))

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
    def fd_structs(self) -> List[FdStruct]:
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

    def __repr__(self):
        return f'<{self.__class__.__name__} PID:{self.pid} PATH:{self.path}>'


class DarwinProcesses(Processes):
    """ manage processes """

    def get_by_pid(self, pid: int) -> Process:
        """ get process object by pid """
        for p in self.list():
            if p.pid == pid:
                return p
        raise ArgumentError(f'failed to locate process with pid: {pid}')

    def get_by_name(self, name: str):
        """ get process object by name """
        for p in self.list():
            if p.name == name:
                return p
        raise ArgumentError(f'failed to locate process with name: {name}')

    def grep(self, name: str) -> List[Process]:
        """ get process list by a name filter """
        result = []
        for p in self.list():
            if name in p.name:
                result.append(p)
        return result

    def get_process_by_listening_port(self, port: int) -> Optional[Process]:
        """ get a process object listening on the specified port """
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
                    return process

    def lsof(self) -> Mapping[int, List[Fd]]:
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
    def fuser(self, path: str) -> List[Process]:
        """get a list of all processes have an open hande to the specified path """
        result = []
        for process in self.list():
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

    def list(self) -> List[Process]:
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
