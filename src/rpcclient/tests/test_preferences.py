import plistlib
from collections.abc import AsyncGenerator
from contextlib import suppress

import pytest
import pytest_asyncio

from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.exceptions import NoSuchPreferenceError


pytestmark = pytest.mark.darwin
DOMAIN = "rpcserver"
USERNAME = "kCFPreferencesAnyUser"
PLIST_PATH = f"/Library/Preferences/{DOMAIN}.plist"


@pytest_asyncio.fixture()
async def tmp_preference(client: DarwinClient) -> AsyncGenerator[None]:
    await client.preferences.cf.set_dict({"key1": "value1"}, DOMAIN, USERNAME)
    await client.preferences.cf.sync(DOMAIN, USERNAME)
    await client.fs.write_file(PLIST_PATH, plistlib.dumps({"key1": "value1"}))
    try:
        yield
    finally:
        with suppress(NoSuchPreferenceError):
            await client.preferences.cf.clear(DOMAIN, USERNAME)
        await client.preferences.cf.sync(DOMAIN, USERNAME)


async def test_cf_get_keys(client: DarwinClient, tmp_preference: None) -> None:
    assert "key1" in await client.preferences.cf.get_keys(DOMAIN, USERNAME)


async def test_cf_get_keys_invalid_preference(client: DarwinClient, tmp_preference: None) -> None:
    with pytest.raises(NoSuchPreferenceError):
        await client.preferences.cf.get_keys("com.apple.invalid_preference_for_sure", USERNAME)


async def test_cf_get_value(client: DarwinClient, tmp_preference: None) -> None:
    assert await client.preferences.cf.get_value("key1", DOMAIN, USERNAME) == "value1"


async def test_cf_get_dict(client: DarwinClient, tmp_preference: None) -> None:
    assert (await client.preferences.cf.get_dict(DOMAIN, USERNAME))["key1"] == "value1"


async def test_cf_set(client: DarwinClient, tmp_preference: None) -> None:
    await client.preferences.cf.set("key2", {"hey": "you"}, DOMAIN, USERNAME)
    assert await client.preferences.cf.get_value("key2", DOMAIN, USERNAME) == {"hey": "you"}


async def test_cf_remove(client: DarwinClient, tmp_preference: None) -> None:
    await client.preferences.cf.remove("key1", DOMAIN, USERNAME)
    assert await client.preferences.cf.get_value("key1", DOMAIN, USERNAME) is None


async def test_cf_set_dict(client: DarwinClient, tmp_preference: None) -> None:
    await client.preferences.cf.get_value("key1", DOMAIN, USERNAME)
    await client.preferences.cf.set_dict({"b": 5}, DOMAIN, USERNAME)
    assert await client.preferences.cf.get_dict(DOMAIN, USERNAME) == {"b": 5}


async def test_cf_update_dict(client: DarwinClient, tmp_preference: None) -> None:
    update_contents = {"a": 5}
    expected_dict = await client.preferences.cf.get_dict(DOMAIN, USERNAME)
    expected_dict.update(update_contents)
    await client.preferences.cf.update_dict(update_contents, DOMAIN, USERNAME)
    assert await client.preferences.cf.get_dict(DOMAIN, USERNAME) == expected_dict


async def test_cf_clear(client: DarwinClient, tmp_preference: None) -> None:
    await client.preferences.cf.clear(DOMAIN, USERNAME)
    with pytest.raises(NoSuchPreferenceError):
        assert not await client.preferences.cf.get_dict(DOMAIN, USERNAME)


async def test_sc_get_keys(client: DarwinClient, tmp_preference: None) -> None:
    keys = await client.preferences.sc.get_keys(PLIST_PATH)
    assert "key1" in keys


async def test_sc_get_dict(client: DarwinClient, tmp_preference: None) -> None:
    dict_ = await client.preferences.sc.get_dict(PLIST_PATH)
    assert "key1" in dict_


async def test_sc_object_keys(client: DarwinClient, tmp_preference: None) -> None:
    async with await client.preferences.sc.open(PLIST_PATH) as pref:
        keys = await pref.keys()
    assert "key1" in keys


async def test_sc_object_set(client: DarwinClient, tmp_preference: None) -> None:
    async with await client.preferences.sc.open(PLIST_PATH) as pref:
        await pref.set("key2", "value2")
    assert (await client.preferences.sc.get_dict(PLIST_PATH))["key2"] == "value2"


async def test_sc_object_set_dict(client: DarwinClient, tmp_preference: None) -> None:
    async with await client.preferences.sc.open(PLIST_PATH) as pref:
        await pref.set_dict({"hey": "you"})
    assert await client.preferences.sc.get_dict(PLIST_PATH) == {"hey": "you"}


async def test_sc_object_update_dict(client: DarwinClient, tmp_preference: None) -> None:
    async with await client.preferences.sc.open(PLIST_PATH) as pref:
        await pref.update_dict({"hey": "you"})
    dict_ = await client.preferences.sc.get_dict(PLIST_PATH)
    assert dict_["key1"] == "value1"
    assert dict_["hey"] == "you"


async def test_sc_object_remove(client: DarwinClient, tmp_preference: None) -> None:
    async with await client.preferences.sc.open(PLIST_PATH) as pref:
        await pref.remove("key1")
    assert "key1" not in await client.preferences.sc.get_dict(PLIST_PATH)


async def test_sc_object_get(client: DarwinClient, tmp_preference: None) -> None:
    async with await client.preferences.sc.open(PLIST_PATH) as pref:
        val = await pref.get("key1")
    assert val == "value1"


async def test_sc_object_get_dict(client: DarwinClient, tmp_preference: None) -> None:
    async with await client.preferences.sc.open(PLIST_PATH) as pref:
        dict_ = await pref.get_dict()
    assert dict_ == {"key1": "value1"}


async def test_sc_object_clear(client: DarwinClient, tmp_preference: None) -> None:
    async with await client.preferences.sc.open(PLIST_PATH) as pref:
        await pref.clear()
    assert not await client.preferences.sc.get_dict(PLIST_PATH)


class TestCustomDomain:
    @pytest_asyncio.fixture(autouse=True)
    async def clear_domain(self, client):
        with suppress(NoSuchPreferenceError):
            # if from some reason this domain already exist, empty it
            await client.preferences.cf.clear(DOMAIN)
            assert await client.preferences.cf.get_keys(DOMAIN) is None

    async def test_set_dict(self, client):
        test_dict = {"KEY1": "VALUE1", "KEY2": "VALUE2"}
        await client.preferences.cf.set_dict(test_dict, DOMAIN)
        assert test_dict == await client.preferences.cf.get_dict(DOMAIN)

    async def test_remove(self, client):
        test_dict = {"KEY1": "VALUE1", "KEY2": "VALUE2"}
        await client.preferences.cf.set_dict(test_dict, DOMAIN)
        await client.preferences.cf.remove("KEY2", DOMAIN)
        test_dict.pop("KEY2")
        assert test_dict == await client.preferences.cf.get_dict(DOMAIN)


async def test_sc_preferences(client):
    async with await client.preferences.sc.open(DOMAIN) as pref:
        if await pref.get_dict() != {}:
            # if from some reason this domain already exist, empty it
            await pref.clear()
            assert await pref.get_dict() == {}

        # test set a full dictionary
        test_dict = {"KEY1": "VALUE1", "KEY2": "VALUE2"}
        await pref.set_dict(test_dict)
        assert test_dict == await pref.get_dict()

        # test set remove a single value
        await pref.remove("KEY2")
        test_dict.pop("KEY2")
        assert test_dict == await pref.get_dict()

        # remove out test data and verify it works
        await pref.clear()
        assert await pref.get_dict() == {}
