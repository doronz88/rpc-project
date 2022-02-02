from collections import namedtuple

from pyzshell.processes import Processes
from pyzshell.structs.darwin import pid_t, MAXPATHLEN

PROC_ALL_PIDS = 1
Process = namedtuple('Process', 'pid path')


class DarwinProcesses(Processes):
    def list(self):
        n = self._client.symbols.proc_listallpids(0, 0)
        pid_buf_size = pid_t.sizeof() * n
        with self._client.safe_malloc(MAXPATHLEN) as path:
            with self._client.safe_malloc(pid_buf_size) as pid_buf:
                pid_buf.item_size = pid_t.sizeof()
                n = self._client.symbols.proc_listallpids(pid_buf, pid_buf_size)

                result = []
                for i in range(n):
                    pid = int(pid_buf[i])
                    path_len = self._client.symbols.proc_pidpath(pid, path, MAXPATHLEN)
                    result.append(Process(pid=pid, path=path.peek(path_len).decode()))
                return result
