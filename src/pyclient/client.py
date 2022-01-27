import atexit
import logging
import os
import sys
import termios
import typing
from select import select
from socket import socket

from construct import Int32ul, Int64ul, Int32sl

from protocol import protocol_message_t, cmd_type_t, pid_t, exec_chunk_t, exec_chunk_type_t, exitcode_t, fd_t

DEFAULT_PORT = 5910
CHUNK_SIZE = 1024


class Client:
    DEFAULT_ARGV = ['/bin/sh']

    def __init__(self, hostname: str, port: int = None):
        self._hostname = hostname
        self._port = port
        self._sock = None
        self.old_settings = None
        self.connect()

    def connect(self):
        self._sock = socket()
        self._sock.connect((self._hostname, self._port))

    def open(self, filename: str, mode: int):
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_OPEN,
            'data': {'filename': filename, 'mode': mode},
        })
        self._sock.sendall(message)
        fd = fd_t.parse(self.recvall(fd_t.sizeof()))
        return fd

    def close(self, fd: int):
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_CLOSE,
            'data': {'fd': fd },
        })
        self._sock.sendall(message)
        err = Int32sl.parse(self.recvall(Int32sl.sizeof()))
        return err

    def read(self, fd: int, size: int = CHUNK_SIZE):
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_READ,
            'data': {'fd': fd, 'size': size},
        })
        self._sock.sendall(message)
        err = Int64ul.parse(self.recvall(Int64ul.sizeof()))
        buf = b''
        if err > 0:
            buf = self.recvall(err)
        return err, buf

    def get_file(self, filename: str) -> bytes:
        fd = self.open(filename, os.O_RDONLY)
        assert fd >= 0
        buf = b''
        while True:
            err, chunk = self.read(fd)
            buf += chunk
            if err == 0:
                break
            elif err < 0:
                raise IOError()
        self.close(fd)
        return buf

    def execute(self, argv: typing.List[str]) -> int:
        message = protocol_message_t.build({
            'cmd_type': cmd_type_t.CMD_EXEC,
            'data': {'argv': argv},
        })
        self._sock.sendall(message)
        pid = pid_t.parse(self._sock.recv(pid_t.sizeof()))
        return pid

    def restore_terminal(self):
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, self.old_settings)

    def prepare_terminal(self):
        fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(fd)

        atexit.register(self.restore_terminal)

        new = termios.tcgetattr(fd)
        new[3] &= ~(termios.ECHO | termios.ICANON)
        new[6][termios.VMIN] = 1
        new[6][termios.VTIME] = 0

        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, new)

    def recvall(self, size: int) -> bytes:
        buf = b''
        while size:
            try:
                chunk = self._sock.recv(size)
            except BlockingIOError:
                continue
            size -= len(chunk)
            buf += chunk
        return buf

    def shell(self, argv: typing.List[str] = None):
        if argv is None:
            argv = self.DEFAULT_ARGV

        pid = self.execute(argv)
        logging.info(f'shell process started as pid: {pid}')

        self._sock.setblocking(False)

        self.prepare_terminal()

        while True:
            rlist, _, xlist = select([sys.stdin, self._sock], [], [self._sock])

            for fd in xlist:
                if fd == self._sock:
                    print('Bye. 👋')
                    return

            for fd in rlist:
                if fd == sys.stdin:
                    buf = os.read(sys.stdin.fileno(), CHUNK_SIZE)
                    self._sock.sendall(buf)
                elif fd == self._sock:
                    try:
                        buf = self.recvall(exec_chunk_t.sizeof())
                    except ConnectionResetError:
                        print('Bye. 👋')
                        return

                    exec_chunk = exec_chunk_t.parse(buf)
                    data = self.recvall(exec_chunk.size)

                    if exec_chunk.chunk_type == exec_chunk_type_t.CMD_EXEC_CHUNK_TYPE_STDOUT:
                        sys.stdout.write(data.decode())
                        sys.stdout.flush()
                    elif exec_chunk.chunk_type == exec_chunk_type_t.CMD_EXEC_CHUNK_TYPE_ERRORCODE:
                        sys.exit(exitcode_t.parse(data))
