from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Optional

from pygments import highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import ObjectiveCLexer

from rpcclient.clients.darwin.objective_c import objc
from rpcclient.clients.darwin.objective_c.objc import Method
from rpcclient.clients.darwin.objective_c.objective_c_class import Class
from rpcclient.clients.darwin.symbol import DarwinSymbol
from rpcclient.core.symbol import Symbol
from rpcclient.core.symbols_jar import SymbolsJar
from rpcclient.exceptions import RpcClientException


class SettingIvarError(RpcClientException):
    """ Raise when trying to set an Ivar too early or when the Ivar doesn't exist. """
    pass


@dataclass
class Ivar:
    name: str
    value: DarwinSymbol
    type_: str
    offset: int


class ObjectiveCSymbol(DarwinSymbol):
    """
    Wrapper object for an objective-c symbol.
    Allowing easier access to its properties, methods and ivars.
    """

    @classmethod
    def create(cls, value: int, client):
        """
        Create an ObjectiveCSymbol object.
        :param value: Symbol address.
        :param rpcclient.darwin.client.Client client: client.
        :return: ObjectiveCSymbol object.
        :rtype: ObjectiveCSymbol
        """
        symbol = super().create(value, client)
        symbol.ivars = []
        symbol.properties = []
        symbol.methods = []
        symbol.class_ = None  # type: Class
        symbol.reload()
        return symbol

    def reload(self):
        """
        Reload object's in-memory layout.
        """
        object_data = self._client.showobject(self)

        ivars_list = [
            Ivar(name=ivar['name'], type_=ivar['type'], offset=ivar['offset'],
                 value=self._client.symbol(ivar['value'])) for ivar in object_data['ivars']
        ]
        methods_list = [
            objc.Method.from_data(method, self._client) for method in object_data['methods']
        ]
        properties_list = [
            objc.Property(name=prop['name'], attributes=objc.convert_encoded_property_attributes(prop['attributes']))
            for prop in object_data['properties']
        ]

        class_object = Symbol.create(object_data['class_address'], self._client)
        class_wrapper = Class(self._client, class_object)

        self.ivars = ivars_list
        self.methods = methods_list
        self.properties = properties_list
        self.class_ = class_wrapper

    def show(self, dump_to: Optional[str] = None, recursive: bool = False):
        """
        Print to terminal the highlighted class description.
        :param dump_to: directory to dump.
        :param recursive: Show methods of super classes.
        """
        formatted = self._to_str(recursive)
        print(highlight(formatted, ObjectiveCLexer(), TerminalTrueColorFormatter(style='native')))

        if dump_to is None:
            return
        (Path(dump_to) / f'{self.class_.name}.m').expanduser().write_text(formatted)

    def objc_call(self, selector: str, *params, **kwargs):
        """
        Make objc_call() from self return ObjectiveCSymbol when it's an objc symbol.
        :param selector: Selector to execute.
        :param params: Additional parameters.
        :return: ObjectiveCSymbol when return type is an objc symbol.
        """
        symbol = super().objc_call(selector, *params, **kwargs)
        try:
            is_objc_type = self.get_method(selector).return_type == 'id'
        except AttributeError:
            is_objc_type = False
        return symbol.objc_symbol if is_objc_type else symbol

    def get_method(self, name: str) -> Method:
        for method in self.methods:
            if method.name == name:
                return method
        raise AttributeError(f'Method "{name}" does not exist')

    def _set_ivar(self, name, value):
        try:
            ivars = self.__getattribute__('ivars')
            class_name = self.__getattribute__('class_').name
        except AttributeError as e:
            raise SettingIvarError from e

        for i, ivar in enumerate(ivars):
            if ivar.name == name:
                size = self.item_size
                if i < len(self.ivars) - 1:
                    size = ivars[i + 1].offset - ivar.offset
                with self.change_item_size(size):
                    self[ivar.offset // size] = value
                    ivar.value = value
                return
        raise SettingIvarError(f'Ivar "{name}" does not exist in "{class_name}"')

    def _to_str(self, recursive=False):
        protocols_buf = f'<{",".join(self.class_.protocols)}>' if self.class_.protocols else ''

        if self.class_.super is not None:
            buf = f'@interface {self.class_.name}: {self.class_.super.name} {protocols_buf}\n'
        else:
            buf = f'@interface {self.class_.name} {protocols_buf}\n'

        # Add ivars
        buf += '{\n'
        for ivar in self.ivars:
            buf += f'\t{ivar.type_} {ivar.name} = 0x{int(ivar.value):x}; // 0x{ivar.offset:x}\n'
        buf += '}\n'

        # Add properties
        for prop in self.properties:
            attrs = prop.attributes
            buf += f'@property ({",".join(attrs.list)}) {prop.attributes.type_} {prop.name};\n'

            if attrs.synthesize is not None:
                buf += f'@synthesize {prop.name} = {attrs.synthesize};\n'

        # Add methods
        methods = self.methods.copy()

        # Add super methods.
        if recursive:
            for sup in self.class_.iter_supers():
                for method in filter(lambda m: m not in methods, sup.methods):
                    methods.append(method)

        # Print class methods first.
        methods.sort(key=lambda m: not m.is_class)

        for method in methods:
            buf += str(method)

        buf += '@end'
        return buf

    @property
    def symbols_jar(self) -> SymbolsJar:
        """ Get a SymbolsJar object for quick operations on all methods """
        jar = SymbolsJar.create(self._client)

        for m in self.methods:
            jar[m.name] = m.address

        return jar

    def __dir__(self):
        result = set()

        for ivar in self.ivars:
            result.add(ivar.name)

        for method in self.methods:
            result.add(method.name.replace(':', '_'))

        for sup in self.class_.iter_supers():
            for method in sup.methods:
                result.add(method.name.replace(':', '_'))

        result.update(list(super().__dir__()))
        return list(result)

    def __getitem__(self, item):
        if isinstance(item, int):
            return super().__getitem__(item)

        # Ivars
        for ivar in self.ivars:
            if ivar.name == item:
                if self._client.is_objc_type(ivar.value):
                    return ivar.value.objc_symbol
                return ivar.value

        # Properties
        for prop in self.properties:
            if prop.name == item:
                return self.objc_call(item)

        # Methods
        for method in self.methods:
            if method.name == item:
                return partial(self.class_.objc_call, item) if method.is_class else partial(self.objc_call, item)

        for sup in self.class_.iter_supers():
            for method in sup.methods:
                if method.name == item:
                    return partial(self.class_.objc_call, item) if method.is_class else partial(self.objc_call, item)

        raise AttributeError(f''''{self.class_.name}' has no attribute {item}''')

    def __getattr__(self, item: str):
        return self[self.class_.sanitize_name(item)]

    def __setitem__(self, key, value):
        if isinstance(key, int):
            super().__setitem__(key, value)
            return

        with suppress(SettingIvarError):
            self._set_ivar(key, value)
            return

    def __setattr__(self, key, value):
        try:
            key = self.__getattribute__('class_').sanitize_name(key)
        except AttributeError:
            pass
        try:
            self._set_ivar(key, value)
        except SettingIvarError:
            super().__setattr__(key, value)

    def __str__(self):
        return self._to_str(False)

    def __repr__(self):
        return f'<{self.__class__.__name__} 0x{int(self):x} Class: {self.class_.name}>'
