"""Bridge a remote target's filesystem to a local WebDAV server.

Runs an async WebDAV server (ASGIWebDAV) inside the rpcclient process. Every
WebDAV request is translated into ``client.fs`` calls against the target, so a
local WebDAV client (e.g. macOS Finder) can browse and edit the remote path as
if it were a mounted volume.
"""

from __future__ import annotations

import asyncio
import logging
import os
import posixpath
from stat import S_ISDIR, S_ISREG
from typing import TYPE_CHECKING, Any

import uvicorn
from asgi_webdav.config import Config, generate_config_from_dict, reinit_global_config
from asgi_webdav.constants import (
    RESPONSE_DATA_BLOCK_SIZE,
    DAVDepth,
    DAVPath,
    DAVResponseBodyGenerator,
    DAVResponseContentRange,
    DAVTime,
)
from asgi_webdav.helpers import generate_etag, guess_type
from asgi_webdav.property import DAVProperty, DAVPropertyBasicData
from asgi_webdav.provider.common import DAVProvider, DAVProviderFeature, get_response_content_range
from asgi_webdav.request import DAVRequest
from asgi_webdav.server import DAVApp
from asgi_webdav.web_dav import PrefixProviderInfo

from rpcclient.core._types import ClientBound, ClientT_co
from rpcclient.exceptions import RpcClientException


if TYPE_CHECKING:
    from rpcclient.core.subsystems.fs import RemotePath


_APPLE_METADATA_NAMES = frozenset({
    ".DS_Store",
    ".localized",
    ".hidden",
    ".Trashes",
    ".apdisk",
    ".metadata_never_index",
    ".VolumeIcon.icns",
})


def _is_apple_metadata(path: DAVPath) -> bool:
    """Whether a WebDAV path is macOS Finder metadata (``.DS_Store`` / AppleDouble ``._*`` / friends)."""
    name = path.name
    return name.startswith("._") or name in _APPLE_METADATA_NAMES


async def _drain(request: DAVRequest) -> None:
    """Consume and discard a request body."""
    more_body = True
    while more_body:
        event = await request.receive()
        more_body = event.get("more_body")


class RpcFsProvider(DAVProvider):
    """A WebDAV provider whose backing store is a remote target's filesystem."""

    type = "rpcfs"
    feature = DAVProviderFeature(content_range=True, home_dir=False)

    def __init__(self, client: Any, root: str, config: Config, prefix: DAVPath, read_only: bool) -> None:
        super().__init__(
            config=config,
            prefix=prefix,
            uri=f"rpcfs://{root}",
            home_dir=False,
            read_only=read_only,
            ignore_property_extra=True,
        )
        self._client = client
        self._root = root.rstrip("/") or "/"

    def __repr__(self) -> str:
        return f"rpcfs://{self._root}"

    def _remote(self, path: DAVPath) -> RemotePath:
        """Return the remote path for a WebDAV path under the served root."""
        joined = self._root
        for part in path.parts:
            joined = joined.rstrip("/") + "/" + part
        return self._client.fs.remote_path(joined)

    def _remote_parent(self, remote: RemotePath) -> RemotePath:
        """Return the parent as a fresh ``remote_path``.

        ``RemotePath.parent`` drops the bound client on Python < 3.12 (pathlib rebuilds it via
        ``_from_parsed_parts``, bypassing ``__init__``), so build the parent explicitly instead.
        """
        return self._client.fs.remote_path(posixpath.dirname(str(remote).rstrip("/")))

    async def _get_res_etag(self, request: DAVRequest) -> str:
        stat_result = await self._remote(request.dist_src_path).stat()
        return generate_etag(stat_result.st_size, stat_result.st_mtime)

    async def _create_dav_property_obj(self, request: DAVRequest, href_path: DAVPath, stat_result: Any) -> DAVProperty:
        is_collection = S_ISDIR(stat_result.st_mode)
        if is_collection:
            basic_data = DAVPropertyBasicData(
                is_collection=is_collection,
                display_name=href_path.name,
                creation_date=DAVTime(stat_result.st_ctime),
                last_modified=DAVTime(stat_result.st_mtime),
            )
        else:
            content_type, content_encoding = guess_type(self.config, href_path.name)
            basic_data = DAVPropertyBasicData(
                is_collection=is_collection,
                display_name=href_path.name,
                creation_date=DAVTime(stat_result.st_ctime),
                last_modified=DAVTime(stat_result.st_mtime),
                content_type="" if content_type is None else content_type,
                content_charset=None,
                content_length=stat_result.st_size,
                content_encoding=content_encoding,
            )
        return DAVProperty(href_path=href_path, is_collection=is_collection, basic_data=basic_data)

    async def _get_dav_property_d0(self, request: DAVRequest, href_path: DAVPath) -> DAVProperty:
        stat_result = await self._remote(href_path).stat()
        return await self._create_dav_property_obj(request, href_path, stat_result)

    async def _do_propfind(self, request: DAVRequest) -> dict[DAVPath, DAVProperty]:
        dav_properties: dict[DAVPath, DAVProperty] = {}
        base = self._remote(request.dist_src_path)
        if not await base.exists():
            return dav_properties

        base_stat = await base.stat()
        dav_properties[request.src_path] = await self._create_dav_property_obj(request, request.src_path, base_stat)

        if request.depth != DAVDepth.ZERO and S_ISDIR(base_stat.st_mode):
            await self._propfind_children(
                dav_properties, request, request.src_path, infinity=request.depth == DAVDepth.INFINITY
            )
        return dav_properties

    async def _propfind_children(
        self,
        dav_properties: dict[DAVPath, DAVProperty],
        request: DAVRequest,
        href_base: DAVPath,
        infinity: bool,
        depth_limit: int = 99,
    ) -> None:
        sub_dir_names: list[str] = []
        for name in await self._client.fs.listdir(str(self._remote(href_base))):
            href_path = href_base.add_child(name)
            if _is_apple_metadata(href_path):
                continue
            try:
                stat_result = await self._remote(href_path).stat()
            except Exception:
                continue
            dav_properties[href_path] = await self._create_dav_property_obj(request, href_path, stat_result)
            if S_ISDIR(stat_result.st_mode) and infinity:
                sub_dir_names.append(name)

        if not infinity or depth_limit <= 0:
            return
        for name in sub_dir_names:
            await self._propfind_children(dav_properties, request, href_base.add_child(name), infinity, depth_limit - 1)

    async def _do_get(
        self, request: DAVRequest
    ) -> tuple[
        int,
        DAVPropertyBasicData | None,
        DAVResponseBodyGenerator | None,
        DAVResponseContentRange | None,
    ]:
        if _is_apple_metadata(request.dist_src_path):
            return 404, None, None, None
        remote = self._remote(request.dist_src_path)
        try:
            stat_result = await remote.stat()
        except RpcClientException:
            return 404, None, None, None

        if S_ISDIR(stat_result.st_mode):
            dav_property = await self._create_dav_property_obj(request, request.src_path, stat_result)
            return 200, dav_property.basic_data, None, None
        if not S_ISREG(stat_result.st_mode):
            # refuse fifos / devices / sockets: opening them blocks the RPC channel and wedges the mount
            return 403, None, None, None

        dav_property = await self._create_dav_property_obj(request, request.src_path, stat_result)

        if not request.ranges:
            return 200, dav_property.basic_data, self._body_generator(remote), None

        # a Range request: macOS Finder / webdavfs reads large files as a series of byte ranges.
        # Answering those with 200 + the whole file makes the client write the full body at the
        # range's offset, corrupting the result. Serve the requested bytes as 206 Partial Content.
        content_range = get_response_content_range(
            request_ranges=request.ranges,
            file_size=dav_property.basic_data.content_length,
        )
        if content_range is None:
            return 200, dav_property.basic_data, self._body_generator(remote), None
        if request.if_range and not request.if_range.match(
            etag=dav_property.basic_data.etag,
            last_modified=dav_property.basic_data.last_modified.http_date,
        ):
            return 416, dav_property.basic_data, None, content_range
        return 206, dav_property.basic_data, self._body_generator(remote, content_range), content_range

    async def _do_head(self, request: DAVRequest) -> tuple[int, DAVPropertyBasicData | None]:
        if _is_apple_metadata(request.dist_src_path):
            return 404, None
        remote = self._remote(request.dist_src_path)
        try:
            stat_result = await remote.stat()
        except RpcClientException:
            return 404, None
        if not (S_ISDIR(stat_result.st_mode) or S_ISREG(stat_result.st_mode)):
            return 403, None
        dav_property = await self._create_dav_property_obj(request, request.src_path, stat_result)
        return 200, dav_property.basic_data

    async def _body_generator(
        self, remote: RemotePath, content_range: DAVResponseContentRange | None = None
    ) -> DAVResponseBodyGenerator:
        async with await self._client.fs.open(str(remote), "r") as f:
            if content_range is None:
                more_body = True
                while more_body:
                    data = await f.read(RESPONSE_DATA_BLOCK_SIZE)
                    more_body = len(data) == RESPONSE_DATA_BLOCK_SIZE
                    yield data, more_body
                return

            await f.seek(content_range.content_start, os.SEEK_SET)
            remaining = content_range.content_end - content_range.content_start + 1
            while remaining > 0:
                data = await f.read(min(remaining, RESPONSE_DATA_BLOCK_SIZE))
                if not data:
                    break
                remaining -= len(data)
                yield data, remaining > 0

    async def _do_put(self, request: DAVRequest) -> int:
        if _is_apple_metadata(request.dist_src_path):
            # swallow Finder metadata writes: report success without touching the remote target
            await _drain(request)
            return 201
        remote = self._remote(request.dist_src_path)
        try:
            stat_result = await remote.stat()
        except RpcClientException:
            stat_result = None
        if stat_result is not None and not S_ISREG(stat_result.st_mode):
            # target exists as a directory / fifo / device: refuse (opening it may block or is invalid)
            return 405
        if not await self._remote_parent(remote).exists():
            return 409

        try:
            async with await self._client.fs.open(str(remote), "w") as f:
                more_body = True
                while more_body:
                    event = await request.receive()
                    more_body = event.get("more_body")
                    data = event.get("body", b"")
                    if data:
                        await f.write(data)
        except RpcClientException:
            return 403
        return 201

    async def _do_delete(self, request: DAVRequest) -> int:
        if _is_apple_metadata(request.dist_src_path):
            return 204
        remote = self._remote(request.dist_src_path)
        if not await remote.exists():
            return 404
        try:
            await remote.remove(recursive=True, force=True)
        except RpcClientException:
            return 403
        return 204

    async def _do_mkcol(self, request: DAVRequest) -> int:
        remote = self._remote(request.dist_src_path)
        if await remote.exists():
            return 405
        if not await self._remote_parent(remote).exists():
            return 409
        try:
            await remote.mkdir()
        except RpcClientException:
            return 403
        return 201

    async def _do_move(self, request: DAVRequest) -> int:
        src = self._remote(request.dist_src_path)
        dst = self._remote(request.dist_dst_path)
        if not await src.exists():
            return 403
        if not await self._remote_parent(dst).exists():
            return 409
        dst_exists = await dst.exists()
        if not request.overwrite and dst_exists:
            return 412
        try:
            if dst_exists:
                await dst.remove(recursive=True, force=True)
            await self._client.fs.rename(str(src), str(dst))
        except RpcClientException:
            return 403
        return 204 if request.overwrite else 201


class WebDavServer:
    """Handle for a running WebDAV server."""

    def __init__(self, uvicorn_server: Any, task: Any, host: str, port: int) -> None:
        self._server = uvicorn_server
        self._task = task
        self.host = host
        self.port = port

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    async def stop(self) -> None:
        self._server.should_exit = True
        await self._task


class WebDav(ClientBound[ClientT_co]):
    """Serve a remote path over WebDAV for local mounting."""

    def __init__(self, client: ClientT_co) -> None:
        self._client = client

    async def serve(self, path: str, *, host: str = "127.0.0.1", port: int = 0, readonly: bool = False) -> WebDavServer:
        """Start a WebDAV server exposing the remote ``path``.

        :param path: remote directory to serve.
        :param host: local interface to bind (default: loopback).
        :param port: local TCP port; 0 picks a free port.
        :param readonly: expose the path read-only.
        :return: a running-server handle with ``url`` and ``stop()``.
        """
        for name in ("asgi_webdav", "uvicorn", "uvicorn.error", "uvicorn.access"):
            logging.getLogger(name).setLevel(logging.WARNING)

        config = generate_config_from_dict({
            "account_mapping": [{"username": "anonymous", "password": "", "permissions": ["+"]}],
            "anonymous": {
                "enable": True,
                "user": {"username": "anonymous", "password": "", "permissions": ["+"]},
                "allow_missing_auth_header": True,
            },
            "provider_mapping": [],
            "logging": {"enable": False},
        })
        reinit_global_config(config)

        app = DAVApp(config)
        provider = RpcFsProvider(client=self._client, root=path, config=config, prefix=DAVPath("/"), read_only=readonly)
        app.web_dav.prefix_provider_mapping = [
            PrefixProviderInfo(
                prefix=DAVPath("/"),
                prefix_weight=1,
                provider=provider,
                home_dir=False,
                read_only=readonly,
                ignore_property_extra=True,
            )
        ]

        uv_config = uvicorn.Config(app, host=host, port=port, log_level="warning", lifespan="off")
        server = uvicorn.Server(uv_config)
        task = asyncio.ensure_future(server.serve())
        while not server.started:
            await asyncio.sleep(0.02)
        bound_port = server.servers[0].sockets[0].getsockname()[1]
        return WebDavServer(server, task, host, bound_port)
