from collections import namedtuple
from typing import Mapping
from dataclasses import dataclass, field
from functools import lru_cache

from objc_types_decoder.decode import decode as decode_type, decode_with_tail

Property = namedtuple('Property', 'name attributes')
PropertyAttributes = namedtuple('PropertyAttributes', 'synthesize type_ list')


def convert_encoded_property_attributes(encoded):
    conversions = {
        'R': lambda x: 'readonly',
        'C': lambda x: 'copy',
        '&': lambda x: 'strong',
        'N': lambda x: 'nonatomic',
        'G': lambda x: 'getter=' + x[1:],
        'S': lambda x: 'setter=' + x[1:],
        'd': lambda x: 'dynamic',
        'W': lambda x: 'weak',
        'P': lambda x: '<garbage-collected>',
        't': lambda x: 'encoding=' + x[1:],
    }

    type_, tail = decode_with_tail(encoded[1:])
    attributes = []
    synthesize = None
    for attr in filter(None, tail.lstrip(',').split(',')):
        if attr[0] in conversions:
            attributes.append(conversions[attr[0]](attr))
        elif attr[0] == 'V':
            synthesize = attr[1:]

    return PropertyAttributes(type_=type_, synthesize=synthesize, list=attributes)


@dataclass
class Method:
    name: str
    address: int = field(compare=False)
    type_: str = field(compare=False)
    return_type: str = field(compare=False)
    is_class: bool = field(compare=False)
    args_types: list = field(compare=False)

    @staticmethod
    def from_data(data: Mapping, client):
        """
        Create Method object from raw data.
        :param data: Data as loaded from get_objectivec_symbol_data.m.
        :param rpcclient.darwin.client.DarwinClient client: Darwin client.
        """
        return Method(
            name=data['name'],
            address=client.symbol(data['address']),
            type_=data['type'],
            return_type=decode_type(data['return_type']),
            is_class=data['is_class'],
            args_types=list(map(decode_type, data['args_types']))
        )

    def __str__(self):
        if ':' in self.name:
            args_names = self.name.split(':')
            name = ' '.join(['{}:({})'.format(*arg) for arg in zip(args_names, self.args_types[2:])])
        else:
            name = self.name
        prefix = '+' if self.is_class else '-'
        return f'{prefix} {name}; // 0x{self.address:x} (returns: {self.return_type})\n'


def _class_data_list(client, class_, function):
    with client.safe_malloc(4) as out_count:
        out_count.item_size = 4
        c_result = client.symbols.get_lazy(function)(class_, out_count)
        count = out_count[0]
    for i in range(count):
        yield c_result[i]
    if c_result:
        client.symbols.free(c_result)


@lru_cache(maxsize=None)
def get_class_protocols(client, class_):
    return [
        client.symbols.protocol_getName(protocol).peek_str()
        for protocol in _class_data_list(client, class_, 'class_copyProtocolList')
    ]


def _iter_class_ivars(client, class_):
    for ivar in _class_data_list(client, class_, 'class_copyIvarList'):
        yield {
            'name': client.symbols.ivar_getName(ivar).peek_str(),
            'type': decode_type(client.symbols.ivar_getTypeEncoding(ivar).peek_str()),
            'offset': client.symbols.ivar_getOffset(ivar),
        }


@lru_cache(maxsize=None)
def get_class_ivars(client, class_):
    return sorted(_iter_class_ivars(client, class_), key=lambda ivar: ivar['offset'])


@lru_cache(maxsize=None)
def get_super(client, class_):
    return client.symbols.class_getSuperclass(class_)


@lru_cache(maxsize=None)
def get_class_name(client, class_):
    return client.symbols.class_getName(class_).peek_str()


def _iter_until_super(client, class_):
    while True:
        yield class_
        class_ = client.symbols.class_getSuperclass(class_)
        if not class_:
            break


def _iter_object_ivars(client, class_, object_):
    for objc_class in _iter_until_super(client, class_):
        for ivar in _class_data_list(client, objc_class, 'class_copyIvarList'):
            yield {
                'name': client.symbols.ivar_getName(ivar).peek_str(),
                'type': decode_type(client.symbols.ivar_getTypeEncoding(ivar).peek_str()),
                'offset': client.symbols.ivar_getOffset(ivar),
                'value': client.symbols.object_getIvar(object_, ivar)
            }


def get_object_ivars(client, class_, object_):
    ivars = sorted(_iter_object_ivars(client, class_, object_), key=lambda ivar: ivar['offset'])
    for i, ivar in enumerate(ivars):
        value = ivar['value']
        if i < len(ivars) - 1:
            # The .fm file returns a 64bit value, regardless of the real size.
            size = ivars[i + 1]['offset'] - ivar['offset']
            ivar['value'] = value & ((2 ** (size * 8)) - 1)
    return ivars


def _iter_class_properties(client, class_):
    for property_ in _class_data_list(client, class_, 'class_copyPropertyList'):
        yield {
            'name': client.symbols.property_getName(property_).peek_str(),
            'attributes': client.symbols.property_getAttributes(property_).peek_str(),
        }


@lru_cache(maxsize=None)
def get_class_properties(client, class_):
    return [
        Property(name=prop['name'], attributes=convert_encoded_property_attributes(prop['attributes']))
        for prop in _iter_class_properties(client, class_)
    ]


def _iter_object_properties(client, class_):
    fetched_properties = []
    for objc_class in _iter_until_super(client, class_):
        for property in _iter_class_properties(client, objc_class):
            if property['name'] in fetched_properties:
                continue
            fetched_properties.append(property['name'])
            yield property


@lru_cache(maxsize=None)
def get_object_properties(client, class_):
    return [
        Property(name=prop['name'], attributes=convert_encoded_property_attributes(prop['attributes']))
        for prop in _iter_object_properties(client, class_)
    ]


def _iter_class_methods(client, class_):
    for method in _class_data_list(client, class_, 'class_copyMethodList'):
        args_types = []
        for arg in range(client.symbols.method_getNumberOfArguments(method)):
            with client.freeing(
                    client.symbols.method_copyArgumentType(method, arg)) as method_arguments_types:
                args_types.append(method_arguments_types.peek_str())
        with client.freeing(client.symbols.method_copyReturnType(method)) as method_return_type:
            return_type = method_return_type.peek_str()
        yield {
            'name': client.symbols.sel_getName(client.symbols.method_getName(method)).peek_str(),
            'address': client.symbols.method_getImplementation(method),
            'type': client.symbols.method_getTypeEncoding(method).peek_str(),
            'return_type': return_type,
            'args_types': args_types,
        }


def _iter_methods(client, class_):
    for method in _iter_class_methods(client, client.symbols.object_getClass(class_)):
        method['is_class'] = True
        yield method
    for method in _iter_class_methods(client, class_):
        method['is_class'] = False
        yield method


@lru_cache(maxsize=None)
def get_class_methods(client, class_):
    return [Method.from_data(method, client) for method in _iter_methods(client, class_)]
