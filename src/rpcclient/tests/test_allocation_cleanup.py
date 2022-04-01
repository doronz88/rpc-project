import gc


def test_allocate_file_fd_context_manager(client, tmp_path):
    # make sure when the test starts, all previous Allocated references are freed
    gc.collect()
    fds_count = len(client.processes.get_by_pid(client.pid).fds)
    with client.fs.open(tmp_path / 'test', 'w'):
        assert fds_count + 1 == len(client.processes.get_by_pid(client.pid).fds)
    assert fds_count == len(client.processes.get_by_pid(client.pid).fds)


def test_allocate_file_fd_explicit_deallocate(client, tmp_path):
    # make sure when the test starts, all previous Allocated references are freed
    gc.collect()
    fds_count = len(client.processes.get_by_pid(client.pid).fds)
    fd = client.fs.open(tmp_path / 'test', 'w')
    assert fds_count + 1 == len(client.processes.get_by_pid(client.pid).fds)
    fd.deallocate()
    assert fds_count == len(client.processes.get_by_pid(client.pid).fds)
