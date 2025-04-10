import pytest

STDOUT_FD = 1
STDERR_FD = 2
TEST_DATA: bytes = b'testtesttest'


@pytest.mark.parametrize('fd', [
    STDOUT_FD,
    STDERR_FD
])
def test_capture_fd(client, fd: int) -> None:
    """
    :param rpcclient.client.Client client:
    :param int fd:
    """
    with client.capture_fd(fd) as cap:
        if -1 == client.symbols.write(fd, TEST_DATA, len(TEST_DATA)):
            client.raise_errno_exception('write to fd failed')
        data = cap.read()
    assert TEST_DATA == data


@pytest.mark.parametrize('fd', [
    STDOUT_FD,
    STDERR_FD
])
def test_fd_cleanup(client, fd: int) -> None:
    """
    :param rpcclient.client.Client client:
    :param int fd:
    """
    fd_count = len(client.processes.get_self().fds)
    with client.capture_fd(fd):
        pass
    assert fd_count == len(client.processes.get_self().fds)
