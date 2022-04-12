from contextlib import closing
from pathlib import Path
from uuid import uuid4

import pytest

from rpcclient.client_factory import create_client, DarwinClient
from rpcclient.exceptions import BadReturnValueError


@pytest.fixture
def client():
    with closing(create_client('127.0.0.1')) as c:
        yield c


@pytest.fixture
def tmp_path(client):
    tmp_path = '/tmp'
    try:
        tmp_path = client.fs.readlink(tmp_path)
    except BadReturnValueError:
        pass
    filename = Path(tmp_path) / uuid4().hex
    client.fs.mkdir(filename, mode=0o777)
    try:
        yield filename
    finally:
        client.fs.remove(filename, recursive=True)


def pytest_addoption(parser):
    parser.addoption('--ci', action='store_true', default=False, help='Don\'t run local only tests')


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        '''local_only: marks tests that require features the CI lacks (deselect with '-m "not local_only"')'''
    )
    config.addinivalue_line('markers', 'darwin: marks tests that require darwin platform to run')


def pytest_collection_modifyitems(config, items):
    skip_local_only = pytest.mark.skip(reason='remove --ci option to run')
    skip_not_darwin = pytest.mark.skip(reason='Darwin system is required for this test')

    with closing(create_client('127.0.0.1')) as c:
        is_darwin = isinstance(c, DarwinClient)

    for item in items:
        if 'local_only' in item.keywords and config.getoption('--ci'):
            # --ci given in cli: skip local only tests.
            item.add_marker(skip_local_only)
        if 'darwin' in item.keywords and not is_darwin:
            # Skip test that require Darwin on non Darwin system
            item.add_marker(skip_not_darwin)
