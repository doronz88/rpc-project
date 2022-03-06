from contextlib import suppress

import pytest

from rpcclient.exceptions import NoSuchPreferenceError

DOMAIN = 'rpcserver'


def test_cf_get_keys(client):
    """
    :param rpcclient.client.Client client:
    """
    assert 'uuid-mappings' in client.preferences.cf.get_keys('com.apple.networkextension.uuidcache',
                                                             'kCFPreferencesAnyUser')


def test_cf_get_keys_invalid_preference(client):
    """
    :param rpcclient.client.Client client:
    """
    with pytest.raises(NoSuchPreferenceError):
        client.preferences.cf.get_keys('com.apple.invalid_preference_for_sure', 'kCFPreferencesAnyUser')


def test_cf_get_value(client):
    """
    :param rpcclient.client.Client client:
    """
    assert 'com.apple.system.diagnostics' in client.preferences.cf.get_value('uuid-mappings',
                                                                             'com.apple.networkextension.uuidcache',
                                                                             'kCFPreferencesAnyUser')


def test_false_test(client):
    print(client.preferences.cf.get_value('drop_all_level', 'com.apple.networkextension.necp',
                                               'kCFPreferencesAnyUser')))
    assert False


def test_cf_get_dict(client):
    """
    :param rpcclient.client.Client client:
    """
    assert 'com.apple.system.diagnostics' in client.preferences.cf.get_dict('com.apple.networkextension.uuidcache',
                                                                            'kCFPreferencesAnyUser')['uuid-mappings']


def test_cf_set(client):
    """
    :param rpcclient.client.Client client:
    """
    uuid_mapping = client.preferences.cf.get_value('uuid-mappings', 'com.apple.networkextension.uuidcache',
                                                   'kCFPreferencesAnyUser')
    client.preferences.cf.set('uuid-mappings', {'hey': 'you'}, 'com.apple.networkextension.uuidcache',
                              'kCFPreferencesAnyUser')
    try:
        assert client.preferences.cf.get_value('uuid-mappings', 'com.apple.networkextension.uuidcache',
                                               'kCFPreferencesAnyUser') == {'hey': 'you'}
    finally:
        client.preferences.cf.set('uuid-mappings', uuid_mapping, 'com.apple.networkextension.uuidcache',
                                  'kCFPreferencesAnyUser')


def test_cf_remove(client):
    uuid_mapping = client.preferences.cf.get_value('uuid-mappings', 'com.apple.networkextension.uuidcache',
                                                   'kCFPreferencesAnyUser')
    client.preferences.cf.remove('uuid-mappings', 'com.apple.networkextension.uuidcache', 'kCFPreferencesAnyUser')
    try:
        assert client.preferences.cf.get_value('uuid-mappings', 'com.apple.networkextension.uuidcache',
                                               'kCFPreferencesAnyUser') is None
    finally:
        client.preferences.cf.set('uuid-mappings', uuid_mapping, 'com.apple.networkextension.uuidcache',
                                  'kCFPreferencesAnyUser')


def test_cf_set_dict(client):
    uuid_mapping = client.preferences.cf.get_value('uuid-mappings', 'com.apple.networkextension.uuidcache',
                                                   'kCFPreferencesAnyUser')
    client.preferences.cf.set_dict({'a': 5}, 'com.apple.networkextension.uuidcache', 'kCFPreferencesAnyUser')
    try:
        client.preferences.cf.get_dict('com.apple.networkextension.uuidcache', 'kCFPreferencesAnyUser') == {'a': 5}
    finally:
        client.preferences.cf.set_dict({'uuid-mappings': uuid_mapping}, 'com.apple.networkextension.uuidcache',
                                       'kCFPreferencesAnyUser')


def test_cf_update_dict(client):
    uuid_mapping = client.preferences.cf.get_value('uuid-mappings', 'com.apple.networkextension.uuidcache',
                                                   'kCFPreferencesAnyUser')
    client.preferences.cf.set_dict({'a': 5}, 'com.apple.networkextension.uuidcache', 'kCFPreferencesAnyUser')
    try:
        client.preferences.cf.get_dict('com.apple.networkextension.uuidcache', 'kCFPreferencesAnyUser') == {
            'a': 5,
            'uuid-mappings': uuid_mapping
        }
    finally:
        client.preferences.cf.set_dict({'uuid-mappings': uuid_mapping}, 'com.apple.networkextension.uuidcache',
                                       'kCFPreferencesAnyUser')


def test_cf_clear(client):
    uuid_mapping = client.preferences.cf.get_value('uuid-mappings', 'com.apple.networkextension.uuidcache',
                                                   'kCFPreferencesAnyUser')
    client.preferences.cf.clear('com.apple.networkextension.uuidcache', 'kCFPreferencesAnyUser')
    try:
        with pytest.raises(NoSuchPreferenceError):
            assert not client.preferences.cf.get_dict('com.apple.networkextension.uuidcache', 'kCFPreferencesAnyUser')
    finally:
        client.preferences.cf.set('uuid-mappings', uuid_mapping, 'com.apple.networkextension.uuidcache',
                                  'kCFPreferencesAnyUser')


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


def test_sc_get_keys(client):
    """
    :param rpcclient.client.Client client:
    """
    keys = client.preferences.sc.get_keys('preferences.plist')
    assert '__VERSION__' in keys
    assert 'Model' in keys


def test_sc_get_dict(client):
    """
    :param rpcclient.client.Client client:
    """
    dict_ = client.preferences.sc.get_dict('preferences.plist')
    assert '__VERSION__' in dict_ and dict_['__VERSION__']
    assert 'Model' in dict_ and dict_['Model']


def test_sc_object_keys(client):
    """
    :param rpcclient.client.Client client:
    """
    with client.preferences.sc.get_preferences_object('preferences.plist') as pref:
        keys = pref.keys
    assert '__VERSION__' in keys
    assert 'Model' in keys


def test_sc_object_set(client):
    """
    :param rpcclient.client.Client client:
    """
    model = client.preferences.sc.get_dict('preferences.plist')['Model']
    try:
        with client.preferences.sc.get_preferences_object('preferences.plist') as pref:
            pref.set('Model', 'MyModel')
        assert client.preferences.sc.get_dict('preferences.plist')['Model'] == 'MyModel'
    finally:
        with client.preferences.sc.get_preferences_object('preferences.plist') as pref:
            pref.set('Model', model)


def test_sc_object_set_dict(client):
    """
    :param rpcclient.client.Client client:
    """
    dict_ = client.preferences.sc.get_dict('preferences.plist')
    try:
        with client.preferences.sc.get_preferences_object('preferences.plist') as pref:
            pref.set_dict({'hey': 'you'})
        assert client.preferences.sc.get_dict('preferences.plist') == {'hey': 'you'}
    finally:
        with client.preferences.sc.get_preferences_object('preferences.plist') as pref:
            pref.set(dict_)


def test_sc_object_get(client):
    """
    :param rpcclient.client.Client client:
    """
    with client.preferences.sc.get_preferences_object('preferences.plist') as pref:
        model = pref.get('Model')
    assert model


def test_sc_object_get_dict(client):
    """
    :param rpcclient.client.Client client:
    """
    with client.preferences.sc.get_preferences_object('preferences.plist') as pref:
        dict_ = pref.get_dict()
    assert '__VERSION__' in dict_ and dict_['__VERSION__']
    assert 'Model' in dict_ and dict_['Model']


def test_sc_preferences(client):
    with client.preferences.sc.get_preferences_object(DOMAIN) as pref:
        if pref.to_dict() != {}:
            # if from some reason this domain already exist, empty it
            pref.clear()
            assert pref.to_dict() == {}

        # test set a full dictionary
        test_dict = {'KEY1': 'VALUE1', 'KEY2': 'VALUE2'}
        pref.set_dict(test_dict)
        assert test_dict == pref.to_dict()

        # test set remove a single value
        pref.remove('KEY2')
        test_dict.pop('KEY2')
        assert test_dict == pref.to_dict()

        # remove out test data and verify it works
        pref.clear()
        assert pref.to_dict() == {}
