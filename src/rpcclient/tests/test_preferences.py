import plistlib
from contextlib import suppress

import pytest

from rpcclient.exceptions import NoSuchPreferenceError

pytestmark = pytest.mark.darwin
DOMAIN = 'rpcserver'
USERNAME = 'kCFPreferencesAnyUser'
PLIST_PATH = f'/Library/Preferences/{DOMAIN}.plist'


@pytest.fixture()
def tmp_preference(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    client.preferences.cf.set_dict({'key1': 'value1'}, DOMAIN, USERNAME)
    client.preferences.cf.sync(DOMAIN, USERNAME)
    client.fs.write_file(PLIST_PATH, plistlib.dumps({'key1': 'value1'}))
    try:
        yield
    finally:
        try:
            client.preferences.cf.clear(DOMAIN, USERNAME)
        except NoSuchPreferenceError:
            pass
        client.preferences.cf.sync(DOMAIN, USERNAME)


def test_cf_get_keys(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    assert 'key1' in client.preferences.cf.get_keys(DOMAIN, USERNAME)


def test_cf_get_keys_invalid_preference(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    with pytest.raises(NoSuchPreferenceError):
        client.preferences.cf.get_keys('com.apple.invalid_preference_for_sure', USERNAME)


def test_cf_get_value(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    assert 'value1' == client.preferences.cf.get_value('key1', DOMAIN, USERNAME)


def test_cf_get_dict(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    assert 'value1' == client.preferences.cf.get_dict(DOMAIN, USERNAME)['key1']


def test_cf_set(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    client.preferences.cf.set('key2', {'hey': 'you'}, DOMAIN, USERNAME)
    assert client.preferences.cf.get_value('key2', DOMAIN, USERNAME) == {'hey': 'you'}


def test_cf_remove(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    client.preferences.cf.remove('key1', DOMAIN, USERNAME)
    assert client.preferences.cf.get_value('key1', DOMAIN, USERNAME) is None


def test_cf_set_dict(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    client.preferences.cf.get_value('key1', DOMAIN, USERNAME)
    client.preferences.cf.set_dict({'b': 5}, DOMAIN, USERNAME)
    assert client.preferences.cf.get_dict(DOMAIN, USERNAME) == {'b': 5}


def test_cf_update_dict(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    update_contents = {'a': 5}
    expected_dict = client.preferences.cf.get_dict(DOMAIN, USERNAME)
    expected_dict.update(update_contents)
    client.preferences.cf.update_dict(update_contents, DOMAIN, USERNAME)
    assert client.preferences.cf.get_dict(DOMAIN, USERNAME) == expected_dict


def test_cf_clear(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    client.preferences.cf.clear(DOMAIN, USERNAME)
    with pytest.raises(NoSuchPreferenceError):
        assert not client.preferences.cf.get_dict(DOMAIN, USERNAME)


def test_sc_get_keys(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    keys = client.preferences.sc.get_keys(PLIST_PATH)
    assert 'key1' in keys


def test_sc_get_dict(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    dict_ = client.preferences.sc.get_dict(PLIST_PATH)
    assert 'key1' in dict_


def test_sc_object_keys(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    with client.preferences.sc.open(PLIST_PATH) as pref:
        keys = pref.keys
    assert 'key1' in keys


def test_sc_object_set(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    with client.preferences.sc.open(PLIST_PATH) as pref:
        pref.set('key2', 'value2')
    assert client.preferences.sc.get_dict(PLIST_PATH)['key2'] == 'value2'


def test_sc_object_set_dict(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    with client.preferences.sc.open(PLIST_PATH) as pref:
        pref.set_dict({'hey': 'you'})
    assert client.preferences.sc.get_dict(PLIST_PATH) == {'hey': 'you'}


def test_sc_object_update_dict(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    with client.preferences.sc.open(PLIST_PATH) as pref:
        pref.update_dict({'hey': 'you'})
    dict_ = client.preferences.sc.get_dict(PLIST_PATH)
    assert dict_['key1'] == 'value1'
    assert dict_['hey'] == 'you'


def test_sc_object_remove(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    with client.preferences.sc.open(PLIST_PATH) as pref:
        pref.remove('key1')
    assert 'key1' not in client.preferences.sc.get_dict(PLIST_PATH)


def test_sc_object_get(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    with client.preferences.sc.open(PLIST_PATH) as pref:
        val = pref.get('key1')
    assert val == 'value1'


def test_sc_object_get_dict(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    with client.preferences.sc.open(PLIST_PATH) as pref:
        dict_ = pref.get_dict()
    assert dict_ == {'key1': 'value1'}


def test_sc_object_clear(client, tmp_preference):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    with client.preferences.sc.open(PLIST_PATH) as pref:
        pref.clear()
    assert not client.preferences.sc.get_dict(PLIST_PATH)


class TestCustomDomain:
    @pytest.fixture(autouse=True)
    def clear_domain(self, client):
        with suppress(NoSuchPreferenceError):
            # if from some reason this domain already exist, empty it
            client.preferences.cf.clear(DOMAIN)
            assert client.preferences.cf.get_keys(DOMAIN) is None

    def test_set_dict(self, client):
        test_dict = {'KEY1': 'VALUE1', 'KEY2': 'VALUE2'}
        client.preferences.cf.set_dict(test_dict, DOMAIN)
        assert test_dict == client.preferences.cf.get_dict(DOMAIN)

    def test_remove(self, client):
        test_dict = {'KEY1': 'VALUE1', 'KEY2': 'VALUE2'}
        client.preferences.cf.set_dict(test_dict, DOMAIN)
        client.preferences.cf.remove('KEY2', DOMAIN)
        test_dict.pop('KEY2')
        assert test_dict == client.preferences.cf.get_dict(DOMAIN)


def test_sc_preferences(client):
    with client.preferences.sc.open(DOMAIN) as pref:
        if pref.get_dict() != {}:
            # if from some reason this domain already exist, empty it
            pref.clear()
            assert pref.get_dict() == {}

        # test set a full dictionary
        test_dict = {'KEY1': 'VALUE1', 'KEY2': 'VALUE2'}
        pref.set_dict(test_dict)
        assert test_dict == pref.get_dict()

        # test set remove a single value
        pref.remove('KEY2')
        test_dict.pop('KEY2')
        assert test_dict == pref.get_dict()

        # remove out test data and verify it works
        pref.clear()
        assert pref.get_dict() == {}
