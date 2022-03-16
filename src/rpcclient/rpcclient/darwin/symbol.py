from rpcclient.exceptions import UnrecognizedSelectorError
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

    @property
    def py(self):
        """ get a python object from a core foundation one """
        if self == 0:
            return None

        cf_type = self._client.symbols.CFGetTypeID(self)
        if cf_type not in self._client.type_decoders:
            return self

        return self._client.type_decoders[cf_type](self)

    @property
    def objc_symbol(self):
        """
        Get an ObjectiveC symbol of the same address
        :return: Object representing the ObjectiveC symbol
        """
        return self._client.objc_symbol(self)
