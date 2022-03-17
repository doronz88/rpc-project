import struct

from rpcclient.exceptions import BadReturnValueError


class Sysctl:
    """ sysctl utils. read man page for sysctl(3) for more details """

    def __init__(self, client):
        self._client = client

    def get_str(self, name: str) -> str:
        """ equivalent of: sysctl <name> """
        return self.get(name).strip(b'\x00').decode()

    def get_int(self, name: str) -> int:
        """ equivalent of: sysctl <name> """
        return struct.unpack('<I', self.get(name))[0]

    def set_int(self, name: str, value: int):
        """ equivalent of: sysctl <name> -w value """
        self.set(name, struct.pack('<I', value))

    def set_str(self, name: str, value: str):
        """ equivalent of: sysctl <name> -w value """
        self.set(name, value.encode() + b'\x00')

    def set(self, name: str, value: bytes):
        """ equivalent of: sysctl <name> -w value """
        if self._client.symbols.sysctlbyname(name, 0, 0, value, len(value)):
            raise BadReturnValueError(f'sysctl() failed: {self._client.last_error}')

    def get(self, name: str) -> bytes:
        """ equivalent of: sysctl <name> """
        oldval_len = 1024
        with self._client.safe_malloc(8) as p_oldval_len:
            p_oldval_len[0] = oldval_len
            with self._client.safe_malloc(oldval_len) as oldval:
                if self._client.symbols.sysctlbyname(name, oldval, p_oldval_len, 0, 0):
                    raise BadReturnValueError(f'sysctl() failed: {self._client.last_error}')
                return oldval.peek(p_oldval_len[0])
