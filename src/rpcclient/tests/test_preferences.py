DOMAIN = 'rpcserver'


def test_cf_preferences(client):
    if client.preferences.cf.get_keys(DOMAIN) is not None:
        # if from some reason this domain already exist, empty it
        client.preferences.cf.clear(DOMAIN)
        assert client.preferences.cf.get_keys(DOMAIN) is None

    # test set a full dictionary
    test_dict = {'KEY1': 'VALUE1', 'KEY2': 'VALUE2'}
    client.preferences.cf.set_dict(test_dict, DOMAIN)
    assert test_dict == client.preferences.cf.get_values(DOMAIN)

    # test set remove a single value
    client.preferences.cf.remove('KEY2', DOMAIN)
    test_dict.pop('KEY2')
    assert test_dict == client.preferences.cf.get_values(DOMAIN)

    # remove out test data and verify it works
    client.preferences.cf.clear(DOMAIN)
    assert client.preferences.cf.get_keys(DOMAIN) is None


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
