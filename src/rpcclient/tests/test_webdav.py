import asyncio
import os
from contextlib import suppress

import click
import httpx
import pytest

from tests._types import Client


def test_webdav_cli_subcommand_registered() -> None:
    from rpcclient.__main__ import rpcclient

    assert isinstance(rpcclient, click.Group)
    assert "webdav" in rpcclient.commands
    option_names = {param.name for param in rpcclient.commands["webdav"].params}
    assert "mount" in option_names


def test_rpcdav_cli_command_registered() -> None:
    from rpcclient.__main__ import rpcdav

    assert isinstance(rpcdav, click.Command)
    param_names = {param.name for param in rpcdav.params}
    assert "hostname" in param_names
    assert "mount" in param_names


def test_served_path_is_positional_argument() -> None:
    from rpcclient.__main__ import rpcclient, rpcdav

    for command in (rpcdav, rpcclient.commands["webdav"]):
        path_param = next(param for param in command.params if param.name == "path")
        assert isinstance(path_param, click.Argument)


def test_mount_requires_mount_tool(monkeypatch) -> None:
    import shutil

    from rpcclient import __main__ as cli

    monkeypatch.setattr(shutil, "which", lambda name: None)

    # --mount on a host without any mount tool must fail early, before connecting
    with pytest.raises(click.UsageError):
        cli._require_mount_tool(mount=True)

    # without --mount the missing tool is irrelevant
    cli._require_mount_tool(mount=False)


@pytest.mark.parametrize("platform, tool", [("darwin", "mount_webdav"), ("win32", "net"), ("linux", "gio")])
def test_webdav_mount_supported_per_platform(monkeypatch, platform, tool) -> None:
    import shutil

    from rpcclient.core import webdav_mount

    monkeypatch.setattr(webdav_mount.sys, "platform", platform)
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/" + name if name == tool else None)
    assert webdav_mount.webdav_mount_supported() is True

    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert webdav_mount.webdav_mount_supported() is False


@pytest.mark.parametrize("platform, expected", [("darwin", ["open", "/mnt"]), ("win32", ["explorer", "/mnt"])])
def test_opener_command_per_platform(monkeypatch, platform, expected) -> None:
    from rpcclient.core import webdav_mount

    monkeypatch.setattr(webdav_mount.sys, "platform", platform)
    assert webdav_mount._opener_command("/mnt") == expected


@pytest.mark.asyncio
async def test_mount_returns_none_when_tool_absent(monkeypatch) -> None:
    import shutil

    from rpcclient.core import webdav_mount

    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert await webdav_mount.mount_webdav_volume("http://127.0.0.1:1234/") is None


@pytest.mark.parametrize(
    "label, expected",
    [
        ("rpc-127.0.0.1-/var/mobile", "rpc-127.0.0.1-var-mobile"),
        ("rpc-127.0.0.1-/", "rpc-127.0.0.1"),
        ("", "webdav"),
    ],
)
def test_sanitize_label(label, expected) -> None:
    from rpcclient.core import webdav_mount

    assert webdav_mount._sanitize_label(label) == expected


@pytest.mark.asyncio
async def test_get_serves_existing_file(client: Client, tmp_path) -> None:
    target = tmp_path / "hello.txt"
    await client.fs.write_file(target, b"hello from remote")

    server = await client.webdav.serve(str(tmp_path), port=0)
    try:
        async with httpx.AsyncClient() as http:
            response = await http.get(f"{server.url}hello.txt")
        assert response.status_code == 200
        assert response.content == b"hello from remote"
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_get_honors_range_request(client: Client, tmp_path) -> None:
    # macOS Finder / webdavfs reads large files as a series of byte ranges. Answering a Range
    # request with 200 + the whole file makes the client write the full body at the range's
    # offset, corrupting the result. The server must reply 206 with exactly the requested bytes.
    payload = bytes((i * 131 + 7) % 256 for i in range(4096)) * 64  # 256 KiB, spans many blocks
    target = tmp_path / "big.bin"
    await client.fs.write_file(target, payload)

    server = await client.webdav.serve(str(tmp_path), port=0)
    try:
        async with httpx.AsyncClient() as http:
            head = await http.head(f"{server.url}big.bin")
            assert head.headers.get("accept-ranges") == "bytes"

            start, end = 100_000, 200_000
            response = await http.get(f"{server.url}big.bin", headers={"Range": f"bytes={start}-{end}"})
            assert response.status_code == 206
            assert response.headers["content-range"] == f"bytes {start}-{end}/{len(payload)}"
            assert response.content == payload[start : end + 1]

            # reassembling sequential ranges must reproduce the file byte-for-byte
            buf = bytearray()
            off = 0
            while off < len(payload):
                stop = min(off + 40_000 - 1, len(payload) - 1)
                part = await http.get(f"{server.url}big.bin", headers={"Range": f"bytes={off}-{stop}"})
                assert part.status_code == 206
                buf += part.content
                off = stop + 1
            assert bytes(buf) == payload
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_put_when_fs_open_fails_returns_error_not_crash(client: Client, tmp_path) -> None:
    # a regular file used as a path component makes the remote open() fail (ENOTDIR),
    # standing in for the read-only-filesystem case Finder hits writing /.DS_Store
    await client.fs.write_file(tmp_path / "afile", b"x")

    server = await client.webdav.serve(str(tmp_path), port=0)
    try:
        async with httpx.AsyncClient() as http:
            response = await http.put(f"{server.url}afile/blocked.txt", content=b"data")
        assert response.status_code == 403
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_put_ds_store_is_swallowed_without_writing_remote(client: Client, tmp_path) -> None:
    server = await client.webdav.serve(str(tmp_path), port=0)
    try:
        async with httpx.AsyncClient() as http:
            response = await http.put(f"{server.url}.DS_Store", content=b"\x00\x01mac metadata")
        assert response.status_code in (200, 201, 204)
    finally:
        await server.stop()

    # the Apple metadata file must NOT have been written to the remote target
    assert not await (tmp_path / ".DS_Store").exists()


@pytest.mark.asyncio
async def test_get_special_file_returns_403_without_wedging(client: Client, tmp_path) -> None:
    # a fifo's read() blocks forever in the target; opening it would hold the single
    # serialized RPC channel and wedge the whole mount. The provider must refuse it.
    os.mkfifo(str(tmp_path / "afifo"))
    await client.fs.write_file(tmp_path / "after.txt", b"still alive")

    server = await client.webdav.serve(str(tmp_path), port=0)
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.get(f"{server.url}afifo")
            assert response.status_code == 403
            # the mount must still serve other requests afterwards (not wedged)
            alive = await http.get(f"{server.url}after.txt")
            assert alive.status_code == 200
            assert alive.content == b"still alive"
    finally:
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(server.stop(), timeout=5)


@pytest.mark.asyncio
async def test_propfind_lists_directory(client: Client, tmp_path) -> None:
    await client.fs.write_file(tmp_path / "a.txt", b"a")
    await client.fs.mkdir(tmp_path / "sub")

    server = await client.webdav.serve(str(tmp_path), port=0)
    try:
        async with httpx.AsyncClient() as http:
            response = await http.request("PROPFIND", server.url, headers={"Depth": "1"})
        assert response.status_code == 207
        assert "a.txt" in response.text
        assert "sub" in response.text
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_put_writes_file(client: Client, tmp_path) -> None:
    server = await client.webdav.serve(str(tmp_path), port=0)
    try:
        async with httpx.AsyncClient() as http:
            response = await http.put(f"{server.url}created.txt", content=b"payload")
        assert response.status_code in (200, 201, 204)
    finally:
        await server.stop()

    assert await client.fs.read_file(tmp_path / "created.txt") == b"payload"


@pytest.mark.asyncio
async def test_delete_removes_file(client: Client, tmp_path) -> None:
    target = tmp_path / "doomed.txt"
    await client.fs.write_file(target, b"bye")

    server = await client.webdav.serve(str(tmp_path), port=0)
    try:
        async with httpx.AsyncClient() as http:
            response = await http.delete(f"{server.url}doomed.txt")
        assert response.status_code in (200, 204)
    finally:
        await server.stop()

    assert not await (tmp_path / "doomed.txt").exists()


@pytest.mark.asyncio
async def test_mkcol_creates_directory(client: Client, tmp_path) -> None:
    server = await client.webdav.serve(str(tmp_path), port=0)
    try:
        async with httpx.AsyncClient() as http:
            response = await http.request("MKCOL", f"{server.url}newdir")
        assert response.status_code == 201
    finally:
        await server.stop()

    assert await (tmp_path / "newdir").is_dir()


@pytest.mark.asyncio
async def test_move_renames_file(client: Client, tmp_path) -> None:
    await client.fs.write_file(tmp_path / "before.txt", b"content")

    server = await client.webdav.serve(str(tmp_path), port=0)
    try:
        async with httpx.AsyncClient() as http:
            response = await http.request(
                "MOVE", f"{server.url}before.txt", headers={"Destination": f"{server.url}after.txt"}
            )
        assert response.status_code in (201, 204)
    finally:
        await server.stop()

    assert not await (tmp_path / "before.txt").exists()
    assert await client.fs.read_file(tmp_path / "after.txt") == b"content"
