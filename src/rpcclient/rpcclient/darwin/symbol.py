import struct
import time

from rpcclient.darwin.consts import kCFNumberSInt64Type, kCFNumberDoubleType
from rpcclient.exceptions import CfSerializationError, UnrecognizedSelector
from rpcclient.symbol import Symbol


class DarwinSymbol(Symbol):
    def objc_call(self, selector, *params):
        """ call an objc method on a given object """
        sel = self._client.symbols.sel_getUid(selector)
        if not self._client.symbols.objc_msgSend(self, self._client.symbols.sel_getUid("respondsToSelector:"), sel):
            raise UnrecognizedSelector(f"unrecognized selector '{selector}' sent to class")

        return self._client.symbols.objc_msgSend(self, sel, *params)

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
