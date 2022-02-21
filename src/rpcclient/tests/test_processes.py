from rpcclient.protocol import DEFAULT_PORT

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
    assert client.processes.get_process_by_listening_port(DEFAULT_PORT).pid == client.pid
