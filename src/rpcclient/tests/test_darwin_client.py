import pytest

pytestmark = pytest.mark.darwin


def test_modules(client):
    """
    :param rpcclient.client.Client client:
    """
    assert '/usr/lib/libSystem.B.dylib' in [module.name for module in client.images]


def test_uname(client):
    """
    :param rpcclient.client.Client client:
    """
    assert client.uname.sysname == 'Darwin'
    assert 'machine' in client.uname


def test_get_class_list(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    assert len(client.get_class_list()) > 0


def test_load_framework(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    assert client.load_framework('Foundation') != 0


def test_load_all_libraries(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    original_count = len(client.images)
    client.load_all_libraries(rebind_symbols=False)  # Pytest not running under ipython, so we can't rebind symbols.'
    assert len(client.images) > original_count


def test_autorelease_pool_object_retain_count(client) -> None:
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    obj = client.cf("tst")
    orig_retain_count = obj.objc_call('retainCount').c_int64
    with client.create_autorelease_pool_ctx():
        obj.objc_call('retain')
        obj.objc_call('autorelease')
        retain_count = obj.objc_call('retainCount').c_int64
        assert retain_count == orig_retain_count + 1
    retain_count = obj.objc_call('retainCount').c_int64
    assert retain_count == orig_retain_count


def test_autorelease_pool_object_retrival(client) -> None:
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    with client.create_autorelease_pool_ctx():
        obj = client.cf('tst')
        pool = client.get_current_autorelease_pool()
        assert obj == pool[0]


def test_autorelease_pool_object_retrival_from_ctx(client) -> None:
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    with client.create_autorelease_pool_ctx() as pool:
        obj = client.cf('tst')
        assert obj == pool.get_autorelease_pool()[0]


def test_autorelease_pool_object_retrival_refresh(client):
    """
    :param rpcclient.darwin.client.DarwinClient client:
    """
    with client.create_autorelease_pool_ctx() as pool:
        obj = client.cf('tst')
        pool = pool.get_autorelease_pool()
        assert obj in pool
        obj2 = client.cf('tst2')
        assert obj2 not in pool
        pool.refresh()
        assert obj2 in pool
