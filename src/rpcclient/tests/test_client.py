import pytest

from rpcclient.core.subsystems.decorator import SubsystemNotAvailable, subsystem
from rpcclient.exceptions import ArgumentError


def _get_subsystems(client) -> list[str]:
    names: set[str] = set()
    for cls in client.__class__.mro():
        for name, attr in vars(cls).items():
            if isinstance(attr, subsystem):
                names.add(name)
    return sorted(names)


def test_peek(client):
    """
    :param rpcclient.client.Client client:
    """
    with client.safe_malloc(0x100) as peekable:
        client.peek(peekable, 0x100)


def test_poke(client):
    """
    :param rpcclient.client.Client client:
    """
    with client.safe_malloc(0x100) as peekable:
        client.poke(peekable, b'a' * 0x100)


@pytest.mark.parametrize('params', [
    ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
    ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
])
def test_16args(client, params):
    """
    :param rpcclient.client.Client client:
    """
    with client.safe_malloc(0x100) as peekable:
        client.symbols.test_16args(peekable, *params)
        for i in range(len(params)):
            assert peekable[i] == params[i]


@pytest.mark.parametrize('va_list_index,params,expected', [
    (2, ['%f', 15.5], '15.500000'),
    (2, ['%f %f', 15.5, 7.3], '15.500000 7.300000'),
    (2, ['%f %f %d', 15.5, 7.3, 42], '15.500000 7.300000 42'),
    (2, ['%f %f %d %d', 15.5, 7.3, 1, 2], '15.500000 7.300000 1 2'),
    (2, ['%f %f %d %d %s', 15.5, 7.3, 1, 2, 'test'], '15.500000 7.300000 1 2 test'),
    (2, ['%f %f %d %d %s %s', 15.5, 7.3, 1, 2, 'test', 'test2'], '15.500000 7.300000 1 2 test test2'),
])
@pytest.mark.arm
def test_va_list_call(client, va_list_index, params, expected):
    """
    :param rpcclient.client.Client client:
    """
    with client.safe_malloc(0x100) as peekable:
        client.symbols.sprintf(peekable, *params, va_list_index=va_list_index)
        assert expected == peekable.peek_str()


@pytest.mark.arm
def test_floating_point_call(client):
    """
    :param rpcclient.client.Client client:
    """
    assert client.symbols.sqrt(16.0, return_float64=True) == 4.0


def test_peek_invalid_address(client):
    """
    :param rpcclient.client.Client client:
    """
    # Server config: -DSAFE_WRITE raises ArgumentError for invalid address; else, ConnectionError.
    with pytest.raises((ArgumentError, ConnectionError)):
        client.peek(0, 0x10)


def test_poke_invalid_address(client):
    """
    :param rpcclient.client.Client client:
    """
    # Server config: -DSAFE_WRITE raises ArgumentError for invalid address; else, ConnectionError.
    with pytest.raises((ArgumentError, ConnectionError)):
        client.poke(0, b'a')


def test_get_dummy_block(client):
    """
    :param rpcclient.client.Client client:
    """
    client.cf([1, 2, 3]).objc_call('enumerateObjectsUsingBlock:', client.get_dummy_block())


def test_listdir(client):
    """
    :param rpcclient.client.Client client:
    """
    entries = client.listdir('/')
    assert entries[0].d_name == '.'
    assert entries[1].d_name == '..'


def test_calloc(client):
    """
    :param rpcclient.client.Client client:
    """
    with client.safe_calloc(0x100) as zeros:
        assert client.peek(zeros, 0x100) == b'\x00' * 0x100


def test_env_get_set(client):
    """
    :param rpcclient.client.Client client:
    """
    client.setenv('TEST', 'test')
    assert client.getenv('TEST') == 'test'


def test_environ(client):
    """
    :param rpcclient.client.Client client:
    """
    assert len(client.environ) > 0
    for e in client.environ:
        assert '=' in e


def test_all_subsystems_initialize(client):
    """
    :param rpcclient.client.Client client:

    Ensure each @subsystem property is initialized and not SubsystemNotAvailable.
    """
    subsystem_names = _get_subsystems(client)
    failures: dict[str, str] = {}

    for name in subsystem_names:
        value = getattr(client, name)
        if isinstance(value, SubsystemNotAvailable):
            failures[name] = repr(value)

    assert not failures, f'Subsystems failed to initialize: {failures}'
