from collections import namedtuple
from dataclasses import dataclass, field
from typing import Mapping

from objc_types_decoder.decode import decode as decode_type
from objc_types_decoder.decode import decode_with_tail

from rpcclient.client import Client

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
    client: Client = field(compare=False)
    address: int = field(compare=False)
    imp: int = field(compare=False)
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
            client=client,
            address=client.symbol(data['address']),
            imp=client.symbol(data['imp']),
            type_=data['type'],
            return_type=decode_type(data['return_type']),
            is_class=data['is_class'],
            args_types=list(map(decode_type, data['args_types']))
        )

    def set_implementation(self, new_imp: int):
        self.client.symbols.method_setImplementation(self.address, new_imp)
        self.imp = self.client.symbol(new_imp)

    def always_return(self, value: bool) -> None:
        """
        Patch the method to always return the given value.
        """
        if value:
            # Exported from rpcserver binary
            ret_val = self.client.symbols.get_true
        else:
            # Exported from rpcserver binary
            ret_val = self.client.symbols.get_false
        self.set_implementation(ret_val)

    def __str__(self):
        if ':' in self.name:
            args_names = self.name.split(':')
            name = ' '.join(['{}:({})'.format(*arg) for arg in zip(args_names, self.args_types[2:])])
        else:
            name = self.name
        prefix = '+' if self.is_class else '-'
        return f'{prefix} {name}; // 0x{self.address:x} (returns: {self.return_type})\n'
