from collections import namedtuple
from functools import partial
from pathlib import Path
from typing import Mapping, Optional

from pygments import highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import ObjectiveCLexer

from rpcclient.darwin import objc
from rpcclient.exceptions import GettingObjectiveCClassError
from rpcclient.symbols_jar import SymbolsJar

Ivar = namedtuple('Ivar', 'name type_ offset')


class Class:
    """
    Wrapper for ObjectiveC Class object.
    """

    def __init__(self, client, class_object=0, class_data: Mapping = None, lazy=False):
        """
        :param rpcclient.darwin.client.DarwinClient client: Darwin client.
        :param rpcclient.darwin.objective_c_symbol.Symbol class_object:
        """
        self._client = client
        self._class_object = class_object
        self.protocols = []
        self.ivars = []
        self.properties = []
        self.methods = []
        self.name = ''
        self.super = None
        if not lazy:
            if class_data is None:
                self.reload()
            else:
                self._load_class_data(class_data)

    @staticmethod
    def from_class_name(client, class_name: str):
        """
        Create ObjectiveC Class from given class name.
        :param rpcclient.darwin.client.DarwinClient client: Darwin client.
        :param class_name: Class name.
        """
        class_object = client.symbols.objc_getClass(class_name)
        class_symbol = Class(client, class_object)
        if class_symbol.name != class_name:
            raise GettingObjectiveCClassError()
        return class_symbol

    @staticmethod
    def sanitize_name(name: str):
        """
        Sanitize python name to ObjectiveC name.
        """
        if name.startswith('_'):
            name = '_' + name[1:].replace('_', ':')
        else:
            name = name.replace('_', ':')
        return name

    def reload(self):
        """
        Reload class object data.
        Should be used whenever the class layout changes (for example, during method swizzling)
        """
        objc_class = self._class_object if self._class_object else self._client.symbols.objc_getClass(self.name)
        class_description = self._client.showclass(objc_class)

        self.super = Class(self._client, class_description['super']) if class_description['super'] else None
        self.name = class_description['name']
        self.protocols = class_description['protocols']
        self.ivars = [
            Ivar(name=ivar['name'], type_=ivar['type'], offset=ivar['offset'])
            for ivar in class_description['ivars']
        ]
        self.properties = [
            objc.Property(name=prop['name'], attributes=objc.convert_encoded_property_attributes(prop['attributes']))
            for prop in class_description['properties']
        ]
        self.methods = [
            objc.Method.from_data(method, self._client) for method in class_description['methods']
        ]

    def show(self, dump_to: Optional[str] = None):
        """
        Print to terminal the highlighted class description.
        :param dump_to: directory to dump.
        """
        formatted = str(self)
        print(highlight(formatted, ObjectiveCLexer(), TerminalTrueColorFormatter(style='native')))

        if dump_to is None:
            return
        (Path(dump_to) / f'{self.name}.m').expanduser().write_text(formatted)

    def objc_call(self, sel: str, *args, **kwargs):
        """
        Invoke a selector on the given class object.
        :param sel: Selector name.
        :return: whatever the selector returned as a symbol.
        """
        return self._class_object.objc_call(sel, *args, **kwargs)

    def get_method(self, name: str):
        """
        Get a specific method implementation.
        :param name: Method name.
        :return: Method.
        """
        for method in self.methods:
            if method.name == name:
                return method

    def iter_supers(self):
        """
        Iterate over the super classes of the class.
        """
        sup = self.super
        while sup is not None:
            yield sup
            sup = sup.super

    def _load_class_data(self, data: Mapping):
        self._class_object = self._client.symbol(data['address'])
        self.super = Class(self._client, data['super']) if data['super'] else None
        self.name = data['name']
        self.protocols = data['protocols']
        self.ivars = [Ivar(name=ivar['name'], type_=ivar['type'], offset=ivar['offset']) for ivar in data['ivars']]
        self.properties = data['properties']
        self.methods = data['methods']

    @property
    def symbols_jar(self) -> SymbolsJar:
        """ Get a SymbolsJar object for quick operations on all methods """
        jar = SymbolsJar.create(self._client)

        for m in self.methods:
            jar[f'[{self.name} {m.name}]'] = m.address

        return jar

    @property
    def bundle_path(self) -> Path:
        return Path(self._client.symbols.objc_getClass('NSBundle')
                    .objc_call('bundleForClass:', self._class_object).objc_call('bundlePath').py())

    def __dir__(self):
        result = set()

        for method in self.methods:
            if method.is_class:
                result.add(method.name.replace(':', '_'))

        for sup in self.iter_supers():
            for method in sup.methods:
                if method.is_class:
                    result.add(method.name.replace(':', '_'))

        result.update(list(super(Class, self).__dir__()))
        return list(result)

    def __str__(self):
        protocol_buf = f'<{",".join(self.protocols)}>' if self.protocols else ''

        if self.super is not None:
            buf = f'@interface {self.name}: {self.super.name} {protocol_buf}\n'
        else:
            buf = f'@interface {self.name} {protocol_buf}\n'

        # Add ivars
        buf += '{\n'
        for ivar in self.ivars:
            buf += f'\t{ivar.type_} {ivar.name}; // 0x{ivar.offset:x}\n'
        buf += '}\n'

        # Add properties
        for prop in self.properties:
            buf += f'@property ({",".join(prop.attributes.list)}) {prop.attributes.type_} {prop.name};\n'

            if prop.attributes.synthesize is not None:
                buf += f'@synthesize {prop.name} = {prop.attributes.synthesize};\n'

        # Add methods
        for method in self.methods:
            buf += str(method)

        buf += '@end'
        return buf

    def __repr__(self):
        return f'<objC Class "{self.name}">'

    def __getitem__(self, item):
        for method in self.methods:
            if method.name == item:
                if method.is_class:
                    return partial(self.objc_call, item)
                else:
                    raise AttributeError(f'{self.name} class has an instance method named {item}, '
                                         f'not a class method')

        for sup in self.iter_supers():
            for method in sup.methods:
                if method.name == item:
                    if method.is_class:
                        return partial(self.objc_call, item)
                    else:
                        raise AttributeError(f'{self.name} class has an instance method named {item}, '
                                             f'not a class method')

        raise AttributeError(f''''{self.name}' class has no attribute {item}''')

    def __getattr__(self, item: str):
        return self[self.sanitize_name(item)]
