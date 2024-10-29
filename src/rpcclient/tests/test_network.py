def test_valid_gethostbyname(client):
    """
    :param rpcclient.client.Client client:
    """
    assert client.network.gethostbyname('google.com') is not None


def test_invalid_gethostbyname(client):
    """
    :param rpcclient.client.Client client:
    """
    assert client.network.gethostbyname('google.com1') is None
