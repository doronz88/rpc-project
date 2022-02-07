def test_stat_sanity(client, tmp_path):
    file = (tmp_path / 'temp.txt')
    file.write_text('h' * 0x10000)
    client_stat = client.fs.stat(file)
    path_stat = file.stat()
    assert path_stat.st_dev == client_stat.st_dev
    assert path_stat.st_ino == client_stat.st_ino  # TODO: verify why this test fails on github workflow
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


def test_scandir_sanity(client, tmp_path):
    with client.fs.scandir(str(tmp_path)) as it:
        entries = [e for e in it]
    assert not entries
    (tmp_path / 'temp.txt').write_text('hello')
    with client.fs.scandir(str(tmp_path)) as it:
        entries = [e for e in it]
    assert len(entries) == 1
    assert entries[0].name == 'temp.txt'
    assert entries[0].path == str(tmp_path / 'temp.txt')
    assert entries[0].is_file()
    assert not entries[0].is_dir()
    assert not entries[0].is_symlink()
