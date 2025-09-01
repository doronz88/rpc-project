from contextlib import closing
from uuid import uuid4

import pytest

from rpcclient.client_manager import ClientManager
from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.clients.ios.client import IosClient
from rpcclient.exceptions import BadReturnValueError
from rpcclient.protos.rpc_pb2 import ARCH_ARM64


@pytest.fixture
def client():
    with closing(ClientManager().create(hostname='127.0.0.1')) as c:
        yield c


@pytest.fixture
def tmp_path(client):
    tmp_path = '/tmp'
    try:
        tmp_path = client.fs.readlink(tmp_path)
    except BadReturnValueError:
        pass
    filename = client.fs.remote_path(tmp_path) / uuid4().hex
    client.fs.mkdir(filename, mode=0o777)
    try:
        yield filename
    finally:
        client.fs.remove(filename, recursive=True)


def pytest_addoption(parser):
    parser.addoption('--ci', action='store_true', default=False, help='Don\'t run local only tests')
    parser.addoption('--local-machine', action='store_true', default=False, help='Run local-machine tests')


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        '''local_only: marks tests that require features the CI lacks (deselect with '-m "not local_only"')'''
    )
    config.addinivalue_line('markers', 'darwin: marks tests that require darwin clients to run')
    config.addinivalue_line('markers', 'ios: marks tests that require ios clients to run')
    config.addinivalue_line('markers', 'local_machine: marks tests that require local_machine to run')
    config.addinivalue_line('markers', 'arm: marks tests that require arm architecture to run')


def pytest_collection_modifyitems(config, items):
    skip_local_only = pytest.mark.skip(reason='remove --ci option to run')
    skip_not_darwin = pytest.mark.skip(reason='Darwin system is required for this test')
    skip_not_ios = pytest.mark.skip(reason='Ios system is required for this test')
    skip_not_arm = pytest.mark.skip(reason='Arm arch is required for this test')
    skip_not_local_machine = pytest.mark.skip(reason='Local machine is required for this test')

    with closing(ClientManager().create(hostname='127.0.0.1')) as c:
        is_darwin = isinstance(c, DarwinClient)
        is_ios = isinstance(c, IosClient)
        is_arm = c.arch == ARCH_ARM64

    for item in items:
        if 'local_only' in item.keywords and config.getoption('--ci'):
            # --ci given in cli: skip local only tests.
            item.add_marker(skip_local_only)
        if 'darwin' in item.keywords and not is_darwin:
            # Skip test that require Darwin on non Darwin system
            item.add_marker(skip_not_darwin)
        if 'ios' in item.keywords and not is_ios:
            # Skip test that require ios
            item.add_marker(skip_not_ios)
        if 'arm' in item.keywords and not is_arm:
            # Skip tests that require arm on non arm architecture
            item.add_marker(skip_not_arm)
        if 'local_machine' in item.keywords and not config.getoption('--local-machine'):
            # Skip test that require local_machine
            item.add_marker(skip_not_local_machine)
