import pytest

from rpcclient.darwin.consts import IOPMUserActiveType

pytestmark = pytest.mark.darwin


def test_copy_assertions_status(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    assertions = client.power.copy_assertions_status()
    assert len(assertions) > 0


def test_copy_assertions_by_process(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    client.power.copy_assertions_by_process()


def test_declare_user_activity(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    name = 'test user activity'
    with client.power.declare_user_activity(name, IOPMUserActiveType.kIOPMUserActiveLocal):
        assert client.power.copy_assertions_by_process()[client.pid][0]['AssertName'] == name


def test_declare_user_network_activity(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    name = 'test user network activity'
    with client.power.declare_network_client_activity(name):
        assert client.power.copy_assertions_by_process()[client.pid][0]['AssertName'] == name


def test_create_assertion(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    name = 'test assertion'
    with client.power.create_assertion(name, 'PreventUserIdleSystemSleep'):
        assert client.power.copy_assertions_by_process()[client.pid][0]['AssertName'] == name
