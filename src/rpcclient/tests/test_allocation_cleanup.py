import gc


def test_allocate_file_fd_context_manager(client, tmp_path):
    # make sure when the test starts, all previous Allocated references are freed
    gc.collect()
    fds_count = len(client.processes.get_by_pid(client.pid).fds)
    with client.fs.open(tmp_path / 'test', 'w'):
        assert fds_count + 1 == len(client.processes.get_by_pid(client.pid).fds)
    assert fds_count == len(client.processes.get_by_pid(client.pid).fds)


def test_allocate_file_fd_gc(client, tmp_path):
    # make sure when the test starts, all previous Allocated references are freed
    gc.collect()
    fds_count = len(client.processes.get_by_pid(client.pid).fds)

    # create a new fd with zero references, so it should be free immediately
    client.fs.open(tmp_path / 'test', 'w')

    # make sure python's GC had a chance to free the newly created fd
    gc.collect()
    assert fds_count == len(client.processes.get_by_pid(client.pid).fds)


def test_allocate_file_fd_explicit_del(client, tmp_path):
    # make sure when the test starts, all previous Allocated references are freed
    gc.collect()
    fds_count = len(client.processes.get_by_pid(client.pid).fds)
    fd = client.fs.open(tmp_path / 'test', 'w')
    assert fds_count + 1 == len(client.processes.get_by_pid(client.pid).fds)
    del fd
    assert fds_count == len(client.processes.get_by_pid(client.pid).fds)


def test_allocate_file_fd_explicit_deallocate(client, tmp_path):
    # make sure when the test starts, all previous Allocated references are freed
    gc.collect()
    fds_count = len(client.processes.get_by_pid(client.pid).fds)
    fd = client.fs.open(tmp_path / 'test', 'w')
    assert fds_count + 1 == len(client.processes.get_by_pid(client.pid).fds)
    fd.deallocate()
    assert fds_count == len(client.processes.get_by_pid(client.pid).fds)
