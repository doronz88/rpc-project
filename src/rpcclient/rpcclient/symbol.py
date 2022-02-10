import ctypes
import os
import struct
import time
from contextlib import contextmanager

from construct import FormatField

from rpcclient.exceptions import CfSerializationError
from rpcclient.structs.darwin_consts import kCFNumberSInt64Type, kCFNumberDoubleType

ADDRESS_SIZE_TO_STRUCT_FORMAT = {1: 'B', 2: 'H', 4: 'I', 8: 'Q'}
RETVAL_BIT_COUNT = 64


class SymbolFormatField(FormatField):
    """
    A Symbol wrapper for construct
    """

    def __init__(self, client):
        super().__init__('<', 'Q')
        self._client = client

    def _parse(self, stream, context, path):
        return self._client.symbol(FormatField._parse(self, stream, context, path))


class Symbol(int):
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

        # public properties
        symbol.retval_bit_count = RETVAL_BIT_COUNT
        symbol.is_retval_signed = True
        symbol.item_size = 8

        # private members
        symbol._client = client
        symbol._offset = 0

        for method_name in Symbol.PROXY_METHODS:
            getattr(symbol.__class__, method_name).__doc__ = \
                getattr(client, method_name).__doc__

        return symbol

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

    def peek_str(self) -> str:
        """ peek string at given address """
        return self.peek(self._client.symbols.strlen(self)).decode()

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

    def read(self, count):
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

    @property
    def c_int64(self) -> int:
        """ cast to c_int64 """
        return ctypes.c_int64(self).value

    @property
    def c_int32(self) -> int:
        """ cast to c_int32 """
        return ctypes.c_int32(self).value

    @property
    def c_int16(self) -> int:
        """ cast to c_int16 """
        return ctypes.c_int16(self).value

    def __add__(self, other):
        try:
            return self._client.symbol(int(self) + other)
        except TypeError:
            return int(self) + other

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        try:
            return self._client.symbol(int(self) - other)
        except TypeError:
            return int(self) - other

    def __rsub__(self, other):
        try:
            return self._client.symbol(other - int(self))
        except TypeError:
            return other - int(self)

    def __mul__(self, other):
        try:
            return self._client.symbol(int(self) * other)
        except TypeError:
            return int(self) * other

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        return self._client.symbol(int(self) / other)

    def __floordiv__(self, other):
        return self._client.symbol(int(self) // other)

    def __mod__(self, other):
        return self._client.symbol(int(self) % other)

    def __and__(self, other):
        return self._client.symbol(int(self) & other)

    def __or__(self, other):
        return self._client.symbol(int(self) | other)

    def __xor__(self, other):
        return self._client.symbol(int(self) ^ other)

    def __getitem__(self, item):
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        addr = self + item * self.item_size
        return self._client.symbol(
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
        return self._client.call(self, args)


class DarwinSymbol(Symbol):
    def objc_call(self, selector, *params):
        """ call an objc method on a given object """
        return self._client.symbols.objc_msgSend(self, self._client.symbols.sel_getUid(selector), *params)

    @property
    def cfdesc(self):
        """
        Get output from CFCopyDescription()
        :return: CFCopyDescription()'s output as a string
        """
        if self == 0:
            return None
        return self._client.symbols.CFCopyDescription(self).py

    @property
    def py(self):
        if self == 0:
            return None

        t = self._client._cf_types[self._client.symbols.CFGetTypeID(self)]
        if t == 'str':
            return self._client.symbols.CFStringGetCStringPtr(self, 0).peek_str()
        if t == 'bool':
            return bool(self._client.symbols.CFBooleanGetValue(self, 0))
        if t == 'number':
            with self._client.safe_malloc(200) as buf:
                if self._client.symbols.CFNumberIsFloatType(self):
                    if not self._client.symbols.CFNumberGetValue(self, kCFNumberDoubleType, buf):
                        raise CfSerializationError(f'failed to deserialize float: {self}')
                    return struct.unpack('<d', buf.peek(8))[0]
                if not self._client.symbols.CFNumberGetValue(self, kCFNumberSInt64Type, buf):
                    raise CfSerializationError(f'failed to deserialize int: {self}')
                return int(buf[0])
        if t == 'date':
            return time.strptime(self.cfdesc, '%Y-%m-%d  %H:%M:%S %z')
        if t == 'data':
            count = self._client.symbols.CFDataGetLength(self)
            return self._client.symbols.CFDataGetBytePtr(self).peek(count)
        if t == 'array':
            result = []
            count = self._client.symbols.CFArrayGetCount(self)
            for i in range(count):
                result.append(self._client.symbols.CFArrayGetValueAtIndex(self, i).py)
            return result
        if t == 'dict':
            result = {}
            count = self._client.symbols.CFArrayGetCount(self)
            with self._client.safe_malloc(8 * count) as keys:
                with self._client.safe_malloc(8 * count) as values:
                    self._client.symbols.CFDictionaryGetKeysAndValues(self, keys, values)
                    for i in range(count):
                        result[keys[i].py] = values[i].py
                    return result
        raise NotImplementedError(f'type: {t}')
