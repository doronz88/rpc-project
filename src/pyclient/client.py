import atexit
import logging
import os
import sys
import termios
import typing
from select import select
from socket import socket

from protocol import protocol_message_t, cmd_type_t, pid_t, exec_chunk_t, exec_chunk_type_t, exitcode_t

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
        # self._sock.setblocking(True)
        while size:
            try:
                chunk = self._sock.recv(size)
            except BlockingIOError:
                continue
            size -= len(chunk)
            buf += chunk
        # self._sock.setblocking(False)
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
