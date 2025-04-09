from typing import Optional

from rpcclient.darwin.symbol import DarwinSymbol

FD_SIZE = 4
BUFFERSIZE = 0x10000


class CaptureFD:
    def __init__(self, client, fd: int) -> None:
        self._client = client
        self.fd: int = fd
        self._backupfd: Optional[DarwinSymbol] = None
        self._pipefd: Optional[DarwinSymbol] = None

    def __enter__(self) -> 'CaptureFD':
        with self._client.safe_malloc(FD_SIZE * 2) as pipefds:
            pipefds.item_size = FD_SIZE
            if 0 != self._client.symbols.pipe(pipefds):
                self._client.raise_errno_exception('pipe failed')
            self._backupfd = self._client.symbols.dup(self.fd)
            if -1 == self._backupfd:
                self._backupfd = None
                self._client.raise_errno_exception('dup fd failed')
            if 0 > self._client.symbols.dup2(pipefds[1], self.fd):
                self._client.raise_errno_exception('dup2 pipe-fd failed')
            if 0 != self._client.symbols.close(pipefds[1]):
                self._client.raise_errno_exception('close pipefd[1] failed')
            self._pipefd = pipefds[0]
        return self

    def __exit__(self, type, value, traceback) -> None:
        if self._backupfd is not None:
            if 0 > self._client.symbols.dup2(self._backupfd, self.fd):
                self._client.raise_errno_exception('dup2 backup-fd failed')
            if 0 != self._client.symbols.close(self._backupfd):
                self._client.raise_errno_exception('close backupfd failed')
            self._backupfd = None
        if self._pipefd is not None:
            if 0 != self._client.symbols.close(self._pipefd):
                self._client.raise_errno_exception(
                    f'close pipefd[0] {self._pipefd} failed')
            self._pipefd = None

    def read(self) -> bytes:
        data = b''
        if self._pipefd is not None:
            with self._client.safe_malloc(BUFFERSIZE) as buff:
                read = BUFFERSIZE
                while read == BUFFERSIZE:
                    read = self._client.symbols.read(
                        self._pipefd,
                        buff,
                        BUFFERSIZE).c_int32
                    if -1 == read:
                        self._client.raise_errno_exception('read fd failed')
                    data += buff.peek(read)
        return data
