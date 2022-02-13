from stat import S_IMODE
import os

import pytest


@pytest.mark.local_only
def test_chown(client, tmp_path):
    file = (tmp_path / 'temp.txt')
    file.touch()
    pre_chown_stat = file.stat()
    client.fs.chown(file, 2, -1)
    post_chown_stat = file.stat()
    assert post_chown_stat.st_uid == 2
    assert pre_chown_stat.st_gid == post_chown_stat.st_gid


def test_chmod(client, tmp_path):
    file = (tmp_path / 'temp.txt')
    file.touch(mode=0o777)
    client.fs.chmod(file, 0o666)
    assert S_IMODE(file.stat().st_mode) == 0o666


def test_remove(client, tmp_path):
    file = (tmp_path / 'temp.txt')
    file.touch()
    client.fs.remove(file)
    assert not file.exists()


def test_mkdir(client, tmp_path):
    dir_ = (tmp_path / 'test_dir')
    client.fs.mkdir(dir_, 0o666)
    assert dir_.exists()


def test_chdir_pwd(client, tmp_path):
    client.fs.chdir(tmp_path)
    assert client.fs.pwd() == str(tmp_path)


def test_symlink(client, tmp_path):
    file = (tmp_path / 'temp.txt')
    symlink = (tmp_path / 'temp1.txt')
    file.touch()
    client.fs.symlink(file, symlink)
    assert symlink.exists()
    assert symlink.is_symlink()
    # Change to when deprecating 3.8
    assert os.readlink(symlink) == str(file)


def test_link(client, tmp_path):
    (tmp_path / 'temp.txt').write_text('hello')
    client.fs.link((tmp_path / 'temp.txt'), (tmp_path / 'temp1.txt'))
    assert (tmp_path / 'temp1.txt').read_text() == 'hello'


def test_listdir(client, tmp_path):
    assert not client.fs.listdir(tmp_path)
    (tmp_path / 'temp.txt').touch()
    assert client.fs.listdir(tmp_path) == ['temp.txt']


def test_scandir_sanity(client, tmp_path):
    entries = [e for e in client.fs.scandir(tmp_path)]
    assert not entries
    (tmp_path / 'temp.txt').write_text('hello')
    entries = [e for e in client.fs.scandir(tmp_path)]
    assert len(entries) == 1
    assert entries[0].name == 'temp.txt'
    assert entries[0].path == str(tmp_path / 'temp.txt')
    assert entries[0].is_file()
    assert not entries[0].is_dir()
    assert not entries[0].is_symlink()


def test_scandir_context_manager(client, tmp_path):
    with client.fs.scandir(tmp_path) as it:
        entries = [e for e in it]
    assert not entries
    (tmp_path / 'temp.txt').write_text('hello')
    with client.fs.scandir(tmp_path) as it:
        entries = [e for e in it]
    assert len(entries) == 1
    assert entries[0].name == 'temp.txt'
    assert entries[0].path == str(tmp_path / 'temp.txt')
    assert entries[0].is_file()
    assert not entries[0].is_dir()
    assert not entries[0].is_symlink()


def test_stat_sanity(client, tmp_path):
    file = (tmp_path / 'temp.txt')
    file.write_text('h' * 0x10000)
    client_stat = client.fs.stat(file)
    path_stat = file.stat()
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
    (tmp_path / 'dir_a').mkdir()
    (tmp_path / 'dir_a' / 'a1.txt').touch()
    (tmp_path / 'dir_a' / 'a2.txt').touch()
    (tmp_path / 'dir_b').mkdir()
    (tmp_path / 'dir_b' / 'b1.txt').touch()
    (tmp_path / 'dir_b' / 'b2.txt').touch()
    assert list(os.walk(tmp_path)) == list(client.fs.walk(tmp_path))
