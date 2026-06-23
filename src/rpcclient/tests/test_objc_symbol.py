import pytest

from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.clients.darwin.consts import NSStringEncoding
from rpcclient.clients.darwin.objective_c.objective_c_class import BoundObjectiveCMethod
from rpcclient.clients.darwin.symbol import DarwinSymbol


pytestmark = pytest.mark.darwin


async def test_method_by_method_name(client: DarwinClient) -> None:
    NSString = await client.objc_get_class("NSString")
    ascii_encoding = NSStringEncoding.NSASCIIStringEncoding
    str1 = (await NSString.stringWithCString_encoding_("Taylor Swift", ascii_encoding)).objc_symbol
    assert await (await str1.objc_call("cStringUsingEncoding:", ascii_encoding)).peek_str() == "Taylor Swift"
    assert await str1.get("length") == len("Taylor Swift")
    lowercase = (await str1.objc_call("lowercaseString")).objc_symbol
    assert await (await lowercase.objc_call("cStringUsingEncoding:", ascii_encoding)).peek_str() == "taylor swift"
    uppercase = (await str1.objc_call("uppercaseString")).objc_symbol
    assert await (await uppercase.objc_call("cStringUsingEncoding:", ascii_encoding)).peek_str() == "TAYLOR SWIFT"


async def test_calling_property(client: DarwinClient) -> None:
    d = await (await client.symbols.objc_getClass("NSMutableDictionary")).objc_call("new")
    # call method
    await d.objc_call("setObject:forKey:", await client.cf("value"), await client.cf("key"))
    # call property
    description = await d.objc_symbol.get("description")
    assert not isinstance(description, BoundObjectiveCMethod)
    assert await description.py() == "{\n    key = value;\n}"


async def test_set_implementation(client: DarwinClient) -> None:
    pid = await client.symbols.getpid()

    isValidJSONObject_ = (await client.objc_get_class("NSJSONSerialization")).get_method("isValidJSONObject:")
    assert isValidJSONObject_ is not None
    await isValidJSONObject_.set_implementation(await client.symbols.getpid.resolve())
    assert await (await client.objc_get_class("NSJSONSerialization")).isValidJSONObject_() == pid


@pytest.mark.parametrize("value", [True, False])
async def test_always_return(client: DarwinClient, value: bool) -> None:
    isValidJSONObject_ = (await client.objc_get_class("NSJSONSerialization")).get_method("isValidJSONObject:")
    assert isValidJSONObject_ is not None
    await isValidJSONObject_.always_return(value)
    assert await (await client.objc_get_class("NSJSONSerialization")).isValidJSONObject_() == value


async def test_ivar_symbol(client: DarwinClient) -> None:
    NSString = await client.objc_get_class("NSString")
    ascii_encoding = NSStringEncoding.NSASCIIStringEncoding
    str1 = (await NSString.stringWithCString_encoding_("Taylor Swift", ascii_encoding)).objc_symbol
    assert isinstance(await str1.get("isa"), DarwinSymbol)
