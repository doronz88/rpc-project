import tempfile
from pathlib import Path
from stat import S_IMODE

import pytest

from rpcclient.clients.darwin.consts import UF_IMMUTABLE
from rpcclient.exceptions import RpcFileNotFoundError, RpcPermissionError


def test_touch(client, tmp_path):
    file = (tmp_path / 'temp.txt')
    client.fs.touch(file, mode=0o666)
    umask = client.symbols.umask(0o22)
    client.symbols.umask(umask)
    assert S_IMODE(client.fs.stat(file).st_mode) == 0o666 & ~umask


def test_chown(client, tmp_path):
    file = (tmp_path / 'temp.txt')
    client.fs.touch(file)
    pre_chown_stat = client.fs.stat(file)
    client.fs.chown(file, 2, -1)
    post_chown_stat = client.fs.stat(file)
    assert post_chown_stat.st_uid == 2
    assert pre_chown_stat.st_gid == post_chown_stat.st_gid


def test_chmod(client, tmp_path):
    file = (tmp_path / 'temp.txt')
    client.fs.touch(file, mode=0o777)
    client.fs.chmod(file, 0o666)
    assert S_IMODE(client.fs.stat(file).st_mode) == 0o666


def test_open(client, tmp_path):
    file = (tmp_path / 'temp.txt')
    with client.fs.open(file, 'rw', 0o666):
        pass
    umask = client.symbols.umask(0o22)
    client.symbols.umask(umask)
    assert S_IMODE(client.fs.stat(file).st_mode) == 0o666 & ~umask


def test_remove(client, tmp_path):
    file = (tmp_path / 'temp.txt')
    client.fs.touch(file)
    client.fs.remove(file)
    assert not client.fs.accessible(file)


def test_mkdir(client, tmp_path):
    dir_ = (tmp_path / 'test_dir')
    client.fs.mkdir(dir_, 0o666)
    assert client.fs.accessible(dir_)


def test_chdir_pwd(client, tmp_path):
    client.fs.chdir(tmp_path)
    assert client.fs.pwd() == str(tmp_path)


def test_symlink(client, tmp_path):
    file = (tmp_path / 'temp.txt')
    symlink = (tmp_path / 'temp1.txt')
    client.fs.touch(file)
    client.fs.symlink(file, symlink)
    assert client.fs.accessible(symlink)
    assert client.fs.readlink(symlink) == str(file)


def test_realpath(client, tmp_path):
    assert client.fs.realpath(tmp_path / '././') == str(tmp_path)


def test_link(client, tmp_path):
    client.fs.write_file(tmp_path / 'temp.txt', b'hello')
    client.fs.link((tmp_path / 'temp.txt'), (tmp_path / 'temp1.txt'))
    assert client.fs.read_file(tmp_path / 'temp1.txt') == b'hello'


def test_listdir(client, tmp_path):
    assert not client.fs.listdir(tmp_path)
    client.fs.touch(tmp_path / 'temp.txt')
    assert client.fs.listdir(tmp_path) == ['temp.txt']


def test_listdir_non_exists(client):
    with pytest.raises(RpcFileNotFoundError):
        client.fs.listdir('/non_exists_path')


def test_push_expand_path(client, tmp_path):
    with tempfile.TemporaryDirectory() as temp_dir:
        local_file = Path(temp_dir) / 'local'
        local_file.touch()
        remote_file = tmp_path / 'temp.txt'
        client.fs.push(local_file, remote_file)
        assert remote_file.exists()


def test_pull_expand_path(client, tmp_path):
    with tempfile.TemporaryDirectory() as temp_dir:
        remote_file = tmp_path / 'temp.txt'
        remote_file.touch()
        local_file = Path(temp_dir) / 'local'
        client.fs.pull(remote_file, local_file)
        assert local_file.exists()


@pytest.mark.parametrize('file_size', [1024, 10240, 102400])
def test_push_pull_with_different_sizes(client, tmp_path, file_size):
    assert not client.fs.listdir(tmp_path)
    local = Path('/tmp/temp.bin')
    local_pull = Path('/tmp/temp2.bin')
    remote = tmp_path / 'temp.bin'

    with open(local, 'wb') as f:
        f.write(b'\0' * file_size)

    client.fs.push(local, remote)

    assert client.fs.lstat(remote).st_size == file_size
    client.fs.pull(remote, local_pull)
    assert local_pull.stat().st_size == file_size
    local.unlink(missing_ok=True)
    local_pull.unlink(missing_ok=True)


def test_pull(client, tmp_path):
    client.fs.touch(tmp_path / 'a')
    with tempfile.TemporaryDirectory() as local_dir:
        local_dir = Path(local_dir)
        client.fs.pull(tmp_path / 'a', local_dir)
        assert (local_dir / 'a').exists()
    with tempfile.TemporaryDirectory() as local_dir:
        local_dir = Path(local_dir)
        client.fs.pull(tmp_path / 'a', local_dir / 'a')
        assert (local_dir / 'a').exists()

    client.fs.mkdir(tmp_path / 'b')
    with tempfile.TemporaryDirectory() as local_dir:
        local_dir = Path(local_dir)
        client.fs.pull(tmp_path / 'b', local_dir, recursive=True)
        assert (local_dir / 'b').exists()
        client.fs.pull(tmp_path / 'b', local_dir / 'b', recursive=True)
        assert (local_dir / 'b' / 'b').exists()


def test_push_pull_dir(client, tmp_path: Path):
    (tmp_path / 'a').touch()
    with tempfile.TemporaryDirectory() as local_dir:
        local_dir = Path(local_dir)
        client.fs.pull(tmp_path, local_dir, recursive=True)
        assert (local_dir / tmp_path.name / 'a').exists()
    with tempfile.TemporaryDirectory() as local_dir:
        local_dir = Path(local_dir)
        (local_dir / 'b').touch()
        client.fs.push(local_dir, tmp_path, recursive=True)
        a = tmp_path / local_dir.name / 'b'
        assert a.exists()


def test_scandir_sanity(client, tmp_path):
    entries = [e for e in client.fs.scandir(tmp_path)]
    assert not entries
    client.fs.write_file(tmp_path / 'temp.txt', b'hello')
    entries = [e for e in client.fs.scandir(tmp_path)]
    assert len(entries) == 1
    assert entries[0].name == 'temp.txt'
    assert entries[0].path == str(tmp_path / 'temp.txt')
    assert entries[0].is_file()
    assert not entries[0].is_dir()
    assert not entries[0].is_symlink()


def test_stat_sanity(client, tmp_path):
    file = tmp_path / 'temp.txt'
    client.fs.write_file(file, 'h' * 0x10000)
    client_stat = client.fs.stat(file)
    path_stat = client.fs.stat(file)
    assert path_stat.st_dev == client_stat.st_dev
    assert path_stat.st_ino == client_stat.st_ino
    assert path_stat.st_mode == client_stat.st_mode
    assert path_stat.st_nlink == client_stat.st_nlink
    assert path_stat.st_uid == client_stat.st_uid
    assert path_stat.st_gid == client_stat.st_gid
    assert path_stat.st_rdev == client_stat.st_rdev
    assert path_stat.st_atime == client_stat.st_atime
    assert path_stat.st_mtime == client_stat.st_mtime
    assert path_stat.st_ctime == client_stat.st_ctime
    assert path_stat.st_size == client_stat.st_size
    assert path_stat.st_blocks == client_stat.st_blocks
    assert path_stat.st_blksize == client_stat.st_blksize
    assert path_stat.st_flags == client_stat.st_flags
    assert path_stat.st_gen == client_stat.st_gen


def test_walk(client, tmp_path):
    client.fs.mkdir(tmp_path / 'dir_a')
    client.fs.touch(tmp_path / 'dir_a' / 'a1.txt')
    client.fs.touch(tmp_path / 'dir_a' / 'a2.txt')
    client.fs.mkdir(tmp_path / 'dir_b')
    client.fs.touch(tmp_path / 'dir_b' / 'b1.txt')
    client.fs.touch(tmp_path / 'dir_b' / 'b2.txt')

    assert list(client.fs.walk(tmp_path)) == [
        (f'{tmp_path}', ['dir_b', 'dir_a'], []),
        (f'{tmp_path}/dir_b', [], ['b2.txt', 'b1.txt']),
        (f'{tmp_path}/dir_a', [], ['a1.txt', 'a2.txt'])
    ]


@pytest.mark.darwin
def test_xattr(client, tmp_path):
    client.fs.setxattr(tmp_path, 'KEY', b'VALUE')
    assert client.fs.getxattr(tmp_path, 'KEY') == b'VALUE'
    assert client.fs.listxattr(tmp_path) == ['KEY']
    assert client.fs.dictxattr(tmp_path) == {'KEY': b'VALUE'}
    client.fs.removexattr(tmp_path, 'KEY')
    assert client.fs.listxattr(tmp_path) == []


@pytest.mark.darwin
def test_chflags(client, tmp_path):
    # create temporary file
    file = tmp_path / 'file'
    with client.fs.open(file, 'w'):
        pass
    # make it immutable
    client.fs.chflags(file, UF_IMMUTABLE)
    # verify we cannot remove it
    with pytest.raises(RpcPermissionError):
        client.fs.remove(file)
    # restore its permissions
    client.fs.chflags(file, 0)
    # verify removal succeeds
    client.fs.remove(file)
