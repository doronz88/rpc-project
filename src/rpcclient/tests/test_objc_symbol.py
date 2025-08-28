import pytest

from rpcclient.clients.darwin.consts import NSStringEncoding
from rpcclient.clients.darwin.symbol import DarwinSymbol

pytestmark = pytest.mark.darwin


def test_method_by_method_name(client):
    NSString = client.objc_get_class('NSString')
    ascii_encoding = NSStringEncoding.NSASCIIStringEncoding
    str1 = NSString.stringWithCString_encoding_('Taylor Swift', ascii_encoding).objc_symbol
    assert str1.cStringUsingEncoding_(ascii_encoding).peek_str() == 'Taylor Swift'
    assert str1.length == len('Taylor Swift')
    assert str1.lowercaseString().objc_symbol.cStringUsingEncoding_(ascii_encoding).peek_str() == 'taylor swift'
    assert str1.uppercaseString().objc_symbol.cStringUsingEncoding_(ascii_encoding).peek_str() == 'TAYLOR SWIFT'


def test_calling_property(client):
    d = client.symbols.objc_getClass('NSMutableDictionary').objc_call('new')
    # call method
    d.objc_call('setObject:forKey:', client.cf('value'), client.cf('key'))
    # call property
    assert '{\n    key = value;\n}' == d.objc_symbol.description.py()


def test_set_implementation(client):
    pid = client.symbols.getpid()

    client.objc_get_class('NSJSONSerialization').get_method('isValidJSONObject:').set_implementation(
        client.symbols.getpid)
    assert client.objc_get_class('NSJSONSerialization').isValidJSONObject_() == pid


@pytest.mark.parametrize('value', [True, False])
def test_always_return(client, value):
    client.objc_get_class('NSJSONSerialization').get_method('isValidJSONObject:').always_return(value)
    assert client.objc_get_class('NSJSONSerialization').isValidJSONObject_() == value


def test_ivar_symbol(client):
    NSString = client.objc_get_class('NSString')
    ascii_encoding = NSStringEncoding.NSASCIIStringEncoding
    str1 = NSString.stringWithCString_encoding_('Taylor Swift', ascii_encoding).objc_symbol
    assert isinstance(str1.isa, DarwinSymbol)
