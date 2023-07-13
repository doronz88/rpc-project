import ctypes
import os
import struct
from contextlib import contextmanager
from typing import List

from capstone import CS_ARCH_ARM64, CS_ARCH_X86, CS_MODE_64, CS_MODE_LITTLE_ENDIAN, Cs, CsInsn
from construct import Container

from rpcclient.protocol import arch_t
from rpcclient.structs.generic import Dl_info

ADDRESS_SIZE_TO_STRUCT_FORMAT = {1: 'B', 2: 'H', 4: 'I', 8: 'Q'}
RETVAL_BIT_COUNT = 64


class Symbol(int):
    """ wrapper for a remote symbol object """

    PROXY_METHODS = ['peek', 'poke']

    @classmethod
    def create(cls, value: int, client):
        """
        Create a Symbol object.
        :param value: Symbol address.
        :param rpcclient.darwin_client.Client client: client.
        :return: Symbol object.
        :rtype: Symbol
        """
        if not isinstance(value, int):
            raise TypeError()

        value &= 0xFFFFFFFFFFFFFFFF

        symbol = cls(value)
        symbol._prepare(client)
        return symbol

    def _clone_from_value(self, value: int):
        return self.create(value, self._client)

    def _prepare(self, client):
        self.retval_bit_count = RETVAL_BIT_COUNT
        self.is_retval_signed = True
        self.item_size = 8

        # private members
        self._client = client
        self._offset = 0

        for method_name in Symbol.PROXY_METHODS:
            getattr(self.__class__, method_name).__doc__ = \
                getattr(client, method_name).__doc__

    @contextmanager
    def change_item_size(self, new_item_size: int):
        """
        Temporarily change item size
        :param new_item_size: Temporary item size
        """
        save_item_size = self.item_size
        self.item_size = new_item_size
        try:
            yield
        finally:
            self.item_size = save_item_size

    def peek(self, count):
        return self._client.peek(self, count)

    def poke(self, buf):
        return self._client.poke(self, buf)

    def peek_str(self, encoding='utf-8') -> str:
        """ peek string at given address """
        return self.peek(self._client.symbols.strlen(self)).decode(encoding)

    def close(self):
        """ Construct compliance. """
        pass

    def seek(self, offset, whence):
        """ Construct compliance. """
        if whence == os.SEEK_CUR:
            self._offset += offset
        elif whence == os.SEEK_SET:
            self._offset = offset - self
        else:
            raise IOError('Unsupported whence')

    def read(self, count: int):
        """ Construct compliance. """
        val = (self + self._offset).peek(count)
        self._offset += count
        return val

    def write(self, buf):
        """ Construct compliance. """
        val = (self + self._offset).poke(buf)
        self._offset += len(buf)
        return val

    def tell(self):
        """ Construct compliance. """
        return self + self._offset

    def disass(self, size=40) -> List[CsInsn]:
        """ peek disassembled lines of 'size' bytes """
        if self._client.arch == arch_t.ARCH_ARM64:
            return list(Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN).disasm(self.peek(size), self))
        else:
            # assume x86_64 by default
            return list(Cs(CS_ARCH_X86, CS_MODE_LITTLE_ENDIAN | CS_MODE_64).disasm(self.peek(size), self))

    @property
    def c_int64(self) -> int:
        """ cast to c_int64 """
        return ctypes.c_int64(self).value

    @property
    def c_uint64(self) -> int:
        """ cast to c_uint64 """
        return ctypes.c_uint64(self).value

    @property
    def c_int32(self) -> int:
        """ cast to c_int32 """
        return ctypes.c_int32(self).value

    @property
    def c_uint32(self) -> int:
        """ cast to c_uint32 """
        return ctypes.c_uint32(self).value

    @property
    def c_int16(self) -> int:
        """ cast to c_int16 """
        return ctypes.c_int16(self).value

    @property
    def c_uint16(self) -> int:
        """ cast to c_uint16 """
        return ctypes.c_uint16(self).value

    @property
    def c_bool(self) -> bool:
        """ cast to c_bool """
        return ctypes.c_bool(self).value

    @property
    def dl_info(self) -> Container:
        dl_info = Dl_info(self._client)
        sizeof = dl_info.sizeof()
        with self._client.safe_malloc(sizeof) as info:
            if 0 == self._client.symbols.dladdr(self, info):
                self._client.raise_errno_exception(f'failed to extract info for: {self}')
            return dl_info.parse_stream(info)

    @property
    def name(self) -> str:
        return self.dl_info.dli_sname

    @property
    def filename(self) -> str:
        return self.dl_info.dli_fname

    def __add__(self, other):
        try:
            return self._clone_from_value(int(self) + other)
        except TypeError:
            return int(self) + other

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        try:
            return self._clone_from_value(int(self) - other)
        except TypeError:
            return int(self) - other

    def __rsub__(self, other):
        try:
            return self._clone_from_value(other - int(self))
        except TypeError:
            return other - int(self)

    def __mul__(self, other):
        try:
            return self._clone_from_value(int(self) * other)
        except TypeError:
            return int(self) * other

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        return self._clone_from_value(int(self) / other)

    def __floordiv__(self, other):
        return self._clone_from_value(int(self) // other)

    def __mod__(self, other):
        return self._clone_from_value(int(self) % other)

    def __and__(self, other):
        return self._clone_from_value(int(self) & other)

    def __or__(self, other):
        return self._clone_from_value(int(self) | other)

    def __xor__(self, other):
        return self._clone_from_value(int(self) ^ other)

    def __getitem__(self, item):
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        addr = self + item * self.item_size
        return self._clone_from_value(
            struct.unpack(self._client._endianness + fmt, self._client.peek(addr, self.item_size))[0])

    def __setitem__(self, item, value):
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        value = struct.pack(self._client._endianness + fmt, int(value))
        self._client.poke(self + item * self.item_size, value)

    def __repr__(self):
        return f'<{type(self).__name__}: {hex(self)}>'

    def __str__(self):
        return hex(self)

    def __call__(self, *args, **kwargs):
        return self._client.call(self, args, **kwargs)
