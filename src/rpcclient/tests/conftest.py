import pytest

from rpcclient.client_factory import create_client


@pytest.fixture
def client():
    try:
        c = create_client('127.0.0.1')
        yield c
    finally:
        c.close()


def pytest_addoption(parser):
    parser.addoption('--ci', action='store_true', default=False, help='Don\'t run local only tests')


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        '''local_only: marks tests that require features the CI lacks (deselect with '-m "not local_only"')'''
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--ci'):
        # --ci given in cli: skip local only tests.
        return
    skip_local_only = pytest.mark.skip(reason='remove --ci option to run')
    for item in items:
        if 'local_only' in item.keywords:
            item.add_marker(skip_local_only)
