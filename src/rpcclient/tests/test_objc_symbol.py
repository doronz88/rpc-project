import pytest

from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.clients.darwin.consts import NSStringEncoding
from rpcclient.clients.darwin.objective_c.objective_c_class import BoundObjectiveCMethod
from rpcclient.clients.darwin.symbol import DarwinSymbol


pytestmark = pytest.mark.darwin


def test_method_by_method_name(client: DarwinClient) -> None:
    NSString = client.objc_get_class("NSString")
    ascii_encoding = NSStringEncoding.NSASCIIStringEncoding
    str1 = NSString.stringWithCString_encoding_("Taylor Swift", ascii_encoding).objc_symbol
    assert str1.cStringUsingEncoding_(ascii_encoding).peek_str() == "Taylor Swift"
    assert str1.length == len("Taylor Swift")
    assert str1.lowercaseString().objc_symbol.cStringUsingEncoding_(ascii_encoding).peek_str() == "taylor swift"
    assert str1.uppercaseString().objc_symbol.cStringUsingEncoding_(ascii_encoding).peek_str() == "TAYLOR SWIFT"


def test_calling_property(client: DarwinClient) -> None:
    d = client.symbols.objc_getClass("NSMutableDictionary").objc_call("new")
    # call method
    d.objc_call("setObject:forKey:", client.cf("value"), client.cf("key"))
    # call property
    description = d.objc_symbol.description
    assert not isinstance(description, BoundObjectiveCMethod)
    assert description.py() == "{\n    key = value;\n}"


def test_set_implementation(client: DarwinClient) -> None:
    pid = client.symbols.getpid()

    isValidJSONObject_ = client.objc_get_class("NSJSONSerialization").get_method("isValidJSONObject:")
    assert isValidJSONObject_ is not None
    isValidJSONObject_.set_implementation(client.symbols.getpid)
    assert client.objc_get_class("NSJSONSerialization").isValidJSONObject_() == pid


@pytest.mark.parametrize("value", [True, False])
def test_always_return(client: DarwinClient, value: bool) -> None:
    isValidJSONObject_ = client.objc_get_class("NSJSONSerialization").get_method("isValidJSONObject:")
    assert isValidJSONObject_ is not None
    isValidJSONObject_.always_return(value)
    assert client.objc_get_class("NSJSONSerialization").isValidJSONObject_() == value


def test_ivar_symbol(client: DarwinClient) -> None:
    NSString = client.objc_get_class("NSString")
    ascii_encoding = NSStringEncoding.NSASCIIStringEncoding
    str1 = NSString.stringWithCString_encoding_("Taylor Swift", ascii_encoding).objc_symbol
    assert isinstance(str1.isa, DarwinSymbol)
