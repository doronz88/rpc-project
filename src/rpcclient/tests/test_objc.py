def test_objc(client):
    d = client.symbols.objc_getClass('NSMutableDictionary').objc_call('new').objc_symbol

    # call method
    d.setObject_forKey_(client.cf('value'), client.cf('key'))

    # call property
    assert '{\n    key = value;\n}' == d.description.py
