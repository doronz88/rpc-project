import tempfile
from pathlib import Path
from stat import S_IMODE

import pytest

from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.clients.darwin.consts import UF_IMMUTABLE
from rpcclient.core.structs.consts import LOCK_EX, LOCK_NB, LOCK_UN
from rpcclient.core.subsystems.fs import RemotePath
from rpcclient.exceptions import RpcFileNotFoundError, RpcPermissionError
from tests._types import SyncClient


async def test_touch(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    file = tmp_path / "temp.txt"
    await client.fs.touch(file, mode=0o666)
    umask = await client.symbols.umask(0o22)
    await client.symbols.umask(umask)
    assert S_IMODE((await client.fs.stat(file)).st_mode) == 0o666 & ~umask


async def test_chown(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    file = tmp_path / "temp.txt"
    await client.fs.touch(file)
    pre_chown_stat = await client.fs.stat(file)
    await client.fs.chown(file, 2, -1)
    post_chown_stat = await client.fs.stat(file)
    assert post_chown_stat.st_uid == 2
    assert pre_chown_stat.st_gid == post_chown_stat.st_gid


async def test_chmod(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    file = tmp_path / "temp.txt"
    await client.fs.touch(file, mode=0o777)
    await client.fs.chmod(file, 0o666)
    assert S_IMODE((await client.fs.stat(file)).st_mode) == 0o666


async def test_open(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    file = tmp_path / "temp.txt"
    async with await client.fs.open(file, "rw", 0o666):
        pass
    umask = await client.symbols.umask(0o22)
    await client.symbols.umask(umask)
    assert S_IMODE((await client.fs.stat(file)).st_mode) == 0o666 & ~umask


async def test_flock(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    file = tmp_path / "lock.txt"
    async with await client.fs.open(file, "w+") as f:
        await f.flock(LOCK_EX | LOCK_NB)
        await f.flock(LOCK_UN)


async def test_remove(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    file = tmp_path / "temp.txt"
    await client.fs.touch(file)
    await client.fs.remove(file)
    assert not await client.fs.accessible(file)


async def test_mkdir(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    dir_ = tmp_path / "test_dir"
    await client.fs.mkdir(dir_, 0o666)
    assert await client.fs.accessible(dir_)


async def test_chdir_pwd(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    await client.fs.chdir(tmp_path)
    assert await client.fs.pwd() == str(tmp_path)


async def test_symlink(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    file = tmp_path / "temp.txt"
    symlink = tmp_path / "temp1.txt"
    await client.fs.touch(file)
    await client.fs.symlink(file, symlink)
    assert await client.fs.accessible(symlink)
    assert await client.fs.readlink(symlink) == str(file)


async def test_realpath(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    assert await client.fs.realpath(tmp_path / "././") == str(tmp_path)


async def test_link(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    await client.fs.write_file(tmp_path / "temp.txt", b"hello")
    await client.fs.link((tmp_path / "temp.txt"), (tmp_path / "temp1.txt"))
    assert await client.fs.read_file(tmp_path / "temp1.txt") == b"hello"


async def test_listdir(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    assert not await client.fs.listdir(tmp_path)
    await client.fs.touch(tmp_path / "temp.txt")
    assert await client.fs.listdir(tmp_path) == ["temp.txt"]


async def test_listdir_non_exists(client):
    with pytest.raises(RpcFileNotFoundError):
        await client.fs.listdir("/non_exists_path")


async def test_push_expand_path(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        local_file = Path(temp_dir) / "local"
        local_file.touch()
        remote_file = tmp_path / "temp.txt"
        await client.fs.push(local_file, remote_file)
        assert await remote_file.exists()


async def test_pull_expand_path(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        remote_file = tmp_path / "temp.txt"
        await remote_file.touch()
        local_file = Path(temp_dir) / "local"
        await client.fs.pull(remote_file, local_file)
        assert local_file.exists()


@pytest.mark.parametrize("file_size", [1024, 10240, 102400])
async def test_push_pull_with_different_sizes(client, tmp_path, file_size):
    assert not await client.fs.listdir(tmp_path)
    local = Path("/tmp/temp.bin")
    local_pull = Path("/tmp/temp2.bin")
    remote = tmp_path / "temp.bin"

    with open(local, "wb") as f:
        f.write(b"\0" * file_size)

    await client.fs.push(local, remote)

    assert (await client.fs.lstat(remote)).st_size == file_size
    await client.fs.pull(remote, local_pull)
    assert local_pull.stat().st_size == file_size
    local.unlink(missing_ok=True)
    local_pull.unlink(missing_ok=True)


async def test_pull(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    await client.fs.touch(tmp_path / "a")
    with tempfile.TemporaryDirectory() as local_dir:
        local_dir = Path(local_dir)
        await client.fs.pull(tmp_path / "a", local_dir)
        assert (local_dir / "a").exists()
    with tempfile.TemporaryDirectory() as local_dir:
        local_dir = Path(local_dir)
        await client.fs.pull(tmp_path / "a", local_dir / "a")
        assert (local_dir / "a").exists()

    await client.fs.mkdir(tmp_path / "b")
    with tempfile.TemporaryDirectory() as local_dir:
        local_dir = Path(local_dir)
        await client.fs.pull(tmp_path / "b", local_dir, recursive=True)
        assert (local_dir / "b").exists()
        await client.fs.pull(tmp_path / "b", local_dir / "b", recursive=True)
        assert (local_dir / "b" / "b").exists()


async def test_push_pull_dir(client: SyncClient, tmp_path: RemotePath[SyncClient]):
    await (tmp_path / "a").touch()
    with tempfile.TemporaryDirectory() as local_dir:
        local_dir = Path(local_dir)
        await client.fs.pull(tmp_path, local_dir, recursive=True)
        assert (local_dir / tmp_path.name / "a").exists()
    with tempfile.TemporaryDirectory() as local_dir:
        local_dir = Path(local_dir)
        (local_dir / "b").touch()
        await client.fs.push(local_dir, tmp_path, recursive=True)
        a = tmp_path / local_dir.name / "b"
        assert a.exists()


async def test_scandir_sanity(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    entries = list(await client.fs.scandir(tmp_path))
    assert not entries
    await client.fs.write_file(tmp_path / "temp.txt", b"hello")
    entries = list(await client.fs.scandir(tmp_path))
    assert len(entries) == 1
    assert entries[0].name == "temp.txt"
    assert entries[0].path == str(tmp_path / "temp.txt")
    assert await entries[0].is_file()
    assert not await entries[0].is_dir()
    assert not await entries[0].is_symlink()


async def test_stat_sanity(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    file = tmp_path / "temp.txt"
    await client.fs.write_file(file, b"h" * 0x10000)
    client_stat = await client.fs.stat(file)
    path_stat = await client.fs.stat(file)
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


async def test_walk(client: SyncClient, tmp_path: RemotePath[SyncClient]) -> None:
    await client.fs.mkdir(tmp_path / "dir_a")
    await client.fs.touch(tmp_path / "dir_a" / "a1.txt")
    await client.fs.touch(tmp_path / "dir_a" / "a2.txt")
    await client.fs.mkdir(tmp_path / "dir_b")
    await client.fs.touch(tmp_path / "dir_b" / "b1.txt")
    await client.fs.touch(tmp_path / "dir_b" / "b2.txt")

    assert [entry async for entry in client.fs.walk(tmp_path)] == [
        (f"{tmp_path}", ["dir_b", "dir_a"], []),
        (f"{tmp_path}/dir_b", [], ["b2.txt", "b1.txt"]),
        (f"{tmp_path}/dir_a", [], ["a1.txt", "a2.txt"]),
    ]


@pytest.mark.darwin
async def test_xattr(client: DarwinClient, tmp_path: RemotePath[DarwinClient]) -> None:
    await client.fs.setxattr(tmp_path, "KEY", b"VALUE")
    assert await client.fs.getxattr(tmp_path, "KEY") == b"VALUE"
    assert await client.fs.listxattr(tmp_path) == ["KEY"]
    assert await client.fs.dictxattr(tmp_path) == {"KEY": b"VALUE"}
    await client.fs.removexattr(tmp_path, "KEY")
    assert await client.fs.listxattr(tmp_path) == []


@pytest.mark.darwin
async def test_chflags(client: DarwinClient, tmp_path: RemotePath[DarwinClient]) -> None:
    # create temporary file
    file = tmp_path / "file"
    async with await client.fs.open(file, "w"):
        pass
    # make it immutable
    await client.fs.chflags(file, UF_IMMUTABLE)
    # verify we cannot remove it
    with pytest.raises(RpcPermissionError):
        await client.fs.remove(file)
    # restore its permissions
    await client.fs.chflags(file, 0)
    # verify removal succeeds
    await client.fs.remove(file)
