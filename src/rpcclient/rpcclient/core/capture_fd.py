from typing import Optional, Tuple

from rpcclient.clients.darwin.structs import POLLIN, pollfd
from rpcclient.core.structs.consts import AF_UNIX, SOCK_STREAM
from rpcclient.core.subsystems.network import Socket

FD_SIZE = 4
READ_SIZE = 0x10000


class CaptureFD:
    """
    Context manager, capturing output to a given `fd`. Read from it using the `read()` method.
    """

    def __init__(self, client, fd: int, sock_buf_size: Optional[int] = None) -> None:
        """
        sock_buf_size is required for captures above 6KB, as any write above this value would block until a read is performed.

        :param rpcclient.client.client.Client client: Current client
        :param fd: FD to capture
        :param sock_buf_size: Buffer size for the capture socket, if not specified, default value is used.
        """
        self._client = client
        self.fd: int = fd
        self._backupfd: Optional[int] = None
        self._socket_pair: Optional[Tuple[int, int]] = None
        self._sock_buf_size: Optional[int] = sock_buf_size

    def __enter__(self) -> 'CaptureFD':
        with self._client.safe_malloc(FD_SIZE * 2) as socket_pair:
            socket_pair.item_size = FD_SIZE
            if 0 != self._client.symbols.socketpair(AF_UNIX, SOCK_STREAM, 0, socket_pair):
                self._client.raise_errno_exception('socketpair failed')
            self._socket_pair = (socket_pair[0].c_int32, socket_pair[1].c_int32)
        if self._sock_buf_size is not None:
            Socket(self._client, self._socket_pair[0]).setbufsize(self._sock_buf_size)
        self._backupfd = self._client.symbols.dup(self.fd).c_int32
        if -1 == self._backupfd:
            self._backupfd = None
            self._client.raise_errno_exception('dup fd failed')
        if 0 > self._client.symbols.dup2(self._socket_pair[0], self.fd):
            self._client.raise_errno_exception('dup2 sock-fd failed')
        return self

    def __exit__(self, type, value, traceback) -> None:
        if self._backupfd is not None:
            if 0 > self._client.symbols.dup2(self._backupfd, self.fd):
                self._client.raise_errno_exception('dup2 backup-fd failed')
            if 0 != self._client.symbols.close(self._backupfd):
                self._client.raise_errno_exception('close backupfd failed')
            self._backupfd = None
        if self._socket_pair is not None:
            if 0 != self._client.symbols.close(self._socket_pair[0]):
                self._client.raise_errno_exception(
                    f'close _socket_pair[0] {self._socket_pair[0]} failed')
            if 0 != self._client.symbols.close(self._socket_pair[1]):
                self._client.raise_errno_exception(
                    f'close _socket_pair[1] {self._socket_pair[1]} failed')
            self._socket_pair = None

    def read(self) -> bytes:
        """ Read the bytes captured from `fd` so far. """
        data = b''
        if self._socket_pair is not None:
            with self._client.safe_malloc(READ_SIZE) as buff:
                read = READ_SIZE
                while read == READ_SIZE:
                    with self._client.safe_malloc(pollfd.sizeof()) as pfds:
                        pfds.poke(pollfd.build({'fd': self._socket_pair[1], 'events': POLLIN, 'revents': 0}))
                        if 1 != self._client.symbols.poll(pfds, 1, 0):
                            return data
                    read = self._client.symbols.read(
                        self._socket_pair[1],
                        buff,
                        READ_SIZE).c_int32
                    if -1 == read:
                        self._client.raise_errno_exception('read fd failed')
                    data += buff.peek(read)
        return data
