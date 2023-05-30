from stat import S_IMODE

import pytest

from rpcclient.darwin.consts import UF_IMMUTABLE
from rpcclient.exceptions import RpcPermissionError


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
