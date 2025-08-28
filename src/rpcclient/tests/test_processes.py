from pathlib import Path

import pytest

from rpcclient.exceptions import LaunchError
from rpcclient.transports import DEFAULT_PORT

LAUNCHD_PID = 1
LAUNCHD_PATH = '/sbin/launchd'


def test_list_sanity(client):
    processes = client.processes.list()
    assert len(processes) > 2  # at least launchd and us should be running
    for p in processes:
        if p.pid == LAUNCHD_PID:
            assert p.path == LAUNCHD_PATH


def test_get_process_by_listening_port(client):
    # there should only be one process listening on this port and that's us
    worker_process = client.processes.get_by_pid(client.pid)
    assert client.processes.get_processes_by_listening_port(DEFAULT_PORT)[0].pid == worker_process.ppid


def test_process_object(client):
    server = client.processes.get_self()
    assert server.pid > 0
    assert len(server.images) > 0
    assert len([img for img in server.images if Path(img.path).name == Path(server.path).name]) > 0
    fds = server.fds
    assert fds[0].fd == 0
    assert fds[1].fd == 1
    assert fds[2].fd == 2


def test_get_memgraph_snapshot(client):
    assert len(client.processes.get_self().parent.get_memgraph_snapshot()) > 0


@pytest.mark.ios
def test_launch_process(client):
    client.processes.launch('com.apple.calculator').kill()


@pytest.mark.ios
def test_launch_invalid_process(client):
    with pytest.raises(LaunchError):
        client.processes.launch('com.apple.cyber')
