import pytest


@pytest.mark.parametrize('data', ['string',
                                  b'bytes',
                                  123,
                                  0.1,
                                  [0, 1, 'abc'],
                                  {'key': 'value'},
                                  [{'key': 'value'}, [1, 2]]])
def test_serialization(client, data):
    assert client.cf(data).py == data
