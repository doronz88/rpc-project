from typing import Optional

from osstatus.cache import ErrorCode, get_possible_error_codes

from rpcclient.core.symbol import Symbol
from rpcclient.exceptions import UnrecognizedSelectorError


class DarwinSymbol(Symbol):
    def objc_call(self, selector, *params, **kwargs):
        """ call an objc method on a given object """
        sel = self._client.symbols.sel_getUid(selector)
        if not self._client.symbols.objc_msgSend(self, self._client.symbols.sel_getUid("respondsToSelector:"), sel):
            raise UnrecognizedSelectorError(f"unrecognized selector '{selector}' sent to class")

        return self._client.symbols.objc_msgSend(self, sel, *params, **kwargs)

    def py(self, *args, **kwargs):
        """ get a python object from a core foundation one """
        if self == 0:
            return None

        return self._client.decode_cf(self)

    @property
    def region(self):
        """ get corresponding region """
        for region in self._client.processes.get_by_pid(self._client.pid).regions:
            if (self >= region.start) and (self <= region.end):
                return region

    @property
    def cfdesc(self):
        """
        Get output from CFCopyDescription()
        :return: CFCopyDescription()'s output as a string
        """
        if self == 0:
            return None
        return self._client.symbols.CFCopyDescription(self).py()

    @property
    def objc_symbol(self):
        """
        Get an ObjectiveC symbol of the same address
        :return: Object representing the ObjectiveC symbol
        """
        return self._client.objc_symbol(self)

    @property
    def osstatus(self) -> Optional[list[ErrorCode]]:
        """ Get possible translation to given error code by querying osstatus """
        return get_possible_error_codes(self)

    @property
    def stripped_value(self) -> 'DarwinSymbol':
        """ Remove PAC upper bits """
        return self._client.symbol(self & 0xfffffffff)
