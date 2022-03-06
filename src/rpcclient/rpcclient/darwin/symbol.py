import datetime
import struct
from typing import List, Mapping

from rpcclient.darwin.consts import kCFNumberSInt64Type, kCFNumberDoubleType, CFStringEncoding
from rpcclient.exceptions import CfSerializationError, UnrecognizedSelectorError
from rpcclient.symbol import Symbol


class DarwinSymbol(Symbol):
    def objc_call(self, selector, *params):
        """ call an objc method on a given object """
        sel = self._client.symbols.sel_getUid(selector)
        if not self._client.symbols.objc_msgSend(self, self._client.symbols.sel_getUid("respondsToSelector:"), sel):
            raise UnrecognizedSelectorError(f"unrecognized selector '{selector}' sent to class")

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

    def _decode_cfnull(self) -> None:
        return None

    def _decode_cfstr(self) -> str:
        ptr = self._client.symbols.CFStringGetCStringPtr(self, CFStringEncoding.kCFStringEncodingMacRoman)
        if ptr:
            return ptr.peek_str('mac_roman')

        with self._client.safe_malloc(4096) as buf:
            if not self._client.symbols.CFStringGetCString(self, buf, 4096, CFStringEncoding.kCFStringEncodingMacRoman):
                raise CfSerializationError('CFStringGetCString failed')
            return buf.peek_str('mac_roman')

    def _decode_cfbool(self) -> bool:
        return bool(self._client.symbols.CFBooleanGetValue(self))

    def _decode_cfnumber(self) -> int:
        with self._client.safe_malloc(200) as buf:
            if self._client.symbols.CFNumberIsFloatType(self):
                if not self._client.symbols.CFNumberGetValue(self, kCFNumberDoubleType, buf):
                    raise CfSerializationError(f'failed to deserialize float: {self}')
                return struct.unpack('<d', buf.peek(8))[0]
            if not self._client.symbols.CFNumberGetValue(self, kCFNumberSInt64Type, buf):
                raise CfSerializationError(f'failed to deserialize int: {self}')
            return int(buf[0])

    def _decode_cfdate(self) -> datetime.datetime:
        return datetime.datetime.strptime(self.cfdesc, '%Y-%m-%d  %H:%M:%S %z')

    def _decode_cfdata(self) -> bytes:
        count = self._client.symbols.CFDataGetLength(self)
        return self._client.symbols.CFDataGetBytePtr(self).peek(count)

    def _decode_cfarray(self) -> List:
        result = []
        count = self._client.symbols.CFArrayGetCount(self)
        for i in range(count):
            result.append(self._client.symbols.CFArrayGetValueAtIndex(self, i).py)
        return result

    def _decode_cfdict(self) -> Mapping:
        result = {}
        count = self._client.symbols.CFArrayGetCount(self)
        with self._client.safe_malloc(8 * count) as keys:
            with self._client.safe_malloc(8 * count) as values:
                self._client.symbols.CFDictionaryGetKeysAndValues(self, keys, values)
                for i in range(count):
                    result[keys[i].py] = values[i].py
                return result

    @property
    def py(self):
        """ get a python object from a core foundation one """
        if self == 0:
            return None

        t = self._client._cf_types[self._client.symbols.CFGetTypeID(self)]
        type_decoders = {
            'null': self._decode_cfnull,
            'str': self._decode_cfstr,
            'bool': self._decode_cfbool,
            'number': self._decode_cfnumber,
            'date': self._decode_cfdate,
            'data': self._decode_cfdata,
            'array': self._decode_cfarray,
            'dict': self._decode_cfdict,
        }
        if t not in type_decoders:
            raise NotImplementedError(f'type: {t}')

        return type_decoders[t]()

    @property
    def objc_symbol(self):
        """
        Get an ObjectiveC symbol of the same address
        :return: Object representing the ObjectiveC symbol
        """
        return self._client.objc_symbol(self)
