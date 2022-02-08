from _socket import htons
from collections import namedtuple
from typing import Optional, List

from construct import Array

from rpcclient.exceptions import BadReturnValueError
from rpcclient.processes import Processes
from rpcclient.structs.consts import AF_INET, AF_INET6
from rpcclient.structs.darwin import pid_t, MAXPATHLEN, PROC_PIDLISTFDS, proc_fdinfo, PROX_FDTYPE_VNODE, \
    vnode_fdinfowithpath, PROC_PIDFDVNODEPATHINFO, proc_taskallinfo, PROC_PIDTASKALLINFO, PROX_FDTYPE_SOCKET, \
    PROC_PIDFDSOCKETINFO, socket_fdinfo, so_kind_t

Process = namedtuple('Process', 'pid path')
FileFd = namedtuple('FileFd', 'fd path')
Ipv4SocketFd = namedtuple('Ipv4SocketFd', 'fd local_port remote_port')  # when remote 0, the socket is for listening
Ipv6SocketFd = namedtuple('Ipv6SocketFd', 'fd local_port remote_port')  # when remote 0, the socket is for listening


class DarwinProcesses(Processes):
    def get_proc_path(self, pid: int) -> Optional[str]:
        """ call proc_pidpath(filename, ...) at remote. review xnu header for more details. """
        with self._client.safe_malloc(MAXPATHLEN) as path:
            path_len = self._client.symbols.proc_pidpath(pid, path, MAXPATHLEN)
            if not path_len:
                return None
            return path.peek(path_len).decode()

    def get_fds(self, pid: int) -> Optional[list]:
        """ get a list of process opened file descriptors """
        result = []
        size = self._client.symbols.proc_pidinfo(pid, PROC_PIDLISTFDS, 0, 0, 0)

        vi_size = 8196  # should be enough for all structs
        with self._client.safe_malloc(vi_size) as vi_buf:
            with self._client.safe_malloc(size) as fdinfo_buf:
                size = int(self._client.symbols.proc_pidinfo(pid, PROC_PIDLISTFDS, 0, fdinfo_buf, size))
                if not size:
                    raise BadReturnValueError('proc_pidinfo(PROC_PIDLISTFDS) failed')

                for fd in Array(size // proc_fdinfo.sizeof(), proc_fdinfo).parse(fdinfo_buf.peek(size)):

                    if fd.proc_fdtype == PROX_FDTYPE_VNODE:
                        # file
                        vs = self._client.symbols.proc_pidfdinfo(pid, fd.proc_fd, PROC_PIDFDVNODEPATHINFO, vi_buf,
                                                                 vi_size)
                        if not vs:
                            raise BadReturnValueError('proc_pidinfo(PROC_PIDFDVNODEPATHINFO) failed')

                        vi = vnode_fdinfowithpath.parse(vi_buf.peek(vnode_fdinfowithpath.sizeof()))
                        result.append(FileFd(fd=fd.proc_fd, path=vi.pvip.vip_path))

                    elif fd.proc_fdtype == PROX_FDTYPE_SOCKET:
                        # socket
                        vs = self._client.symbols.proc_pidfdinfo(pid, fd.proc_fd, PROC_PIDFDSOCKETINFO, vi_buf,
                                                                 vi_size)
                        if not vs:
                            raise BadReturnValueError('proc_pidinfo(PROC_PIDFDSOCKETINFO) failed')

                        vi = socket_fdinfo.parse(vi_buf.peek(vi_size))
                        if vi.psi.soi_family == AF_INET and vi.psi.soi_kind == so_kind_t.SOCKINFO_TCP:
                            local_port = htons(vi.psi.soi_proto.pri_in.insi_lport)
                            remote_port = htons(vi.psi.soi_proto.pri_in.insi_fport)
                            result.append(Ipv4SocketFd(fd=fd.proc_fd, local_port=local_port, remote_port=remote_port))

                        elif vi.psi.soi_family == AF_INET6 and vi.psi.soi_kind == so_kind_t.SOCKINFO_TCP:
                            local_port = htons(vi.psi.soi_proto.pri_in.insi_lport)
                            remote_port = htons(vi.psi.soi_proto.pri_in.insi_fport)
                            result.append(Ipv6SocketFd(fd=fd.proc_fd, local_port=local_port, remote_port=remote_port))
            return result

    def get_task_all_info(self, pid: int):
        """ get a list of process opened file descriptors """
        with self._client.safe_malloc(proc_taskallinfo.sizeof()) as pti:
            if not self._client.symbols.proc_pidinfo(pid, PROC_PIDTASKALLINFO, 0, pti, proc_taskallinfo.sizeof()):
                raise BadReturnValueError('proc_pidinfo(PROC_PIDTASKALLINFO) failed')
            return proc_taskallinfo.parse_stream(pti)

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
                result.append(Process(pid=pid, path=self.get_proc_path(pid)))
            return result
