import asyncio
import logging
import os
import socket
import subprocess
import urllib.request

import requests
import zyncio

from rpcclient.exceptions import FailedToConnectError
from rpcclient.protocol.rpc_bridge import AsyncRpcBridge, SyncRpcBridge
from rpcclient.utils import zync_sleep


logger = logging.getLogger(__name__)

DEFAULT_PORT = 5910
PROJECT_URL = "https://api.github.com/repos/doronz88/rpc-project/releases/latest"
BINARY_NAME = "rpcserver_macosx"


@zyncio.zfunc
async def create_tcp(
    zync_mode: zyncio.Mode,
    *,
    hostname: str | None = None,
    host: str | None = None,
    port: int = DEFAULT_PORT,
    timeout: float | None = None,
) -> SyncRpcBridge | AsyncRpcBridge:
    """Connect via TCP and return an `RpcBridge`."""
    target = hostname or host
    if not target:
        raise TypeError('create_tcp(): provide "hostname" or "host"')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        if zync_mode is zyncio.SYNC:
            if timeout is not None:
                s.settimeout(timeout)
            s.connect((target, port))
            s.settimeout(None)
        else:
            s.setblocking(False)
            await asyncio.wait_for(
                asyncio.get_running_loop().sock_connect(s, (target, port)),
                timeout,
            )
    except ConnectionRefusedError as e:
        s.close()
        raise FailedToConnectError() from e

    bridge_class = SyncRpcBridge if zync_mode is zyncio.SYNC else AsyncRpcBridge

    return await bridge_class.connect.z(s)


@zyncio.zfunc
async def create_local(
    zync_mode: zyncio.Mode,
    *,
    project_url: str = PROJECT_URL,
    binary_name: str = BINARY_NAME,
    poll_interval: float = 0.1,
) -> SyncRpcBridge | AsyncRpcBridge:
    """
    Download the latest rpcserver release asset, spawn it locally on a free port,
    and connect via TCP. Returns an `RpcBridge`.
    """
    resp = requests.get(project_url)
    resp.raise_for_status()
    for asset in resp.json().get("assets", []):
        if asset.get("name") == binary_name:
            url = asset["browser_download_url"]
            logger.info("Downloading %s from %s", binary_name, url)
            urllib.request.urlretrieve(url, binary_name)
            os.chmod(binary_name, os.stat(binary_name).st_mode | 0o100)
            break

    # pick a free port
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.close()

    # spawn
    subprocess.Popen([f"./{binary_name}", "-p", str(port)], cwd=os.getcwd())
    logger.info("rpcserver launched on port %d", port)

    # poll until connectable
    while True:
        try:
            return await create_tcp.run_zync(zync_mode, hostname="127.0.0.1", port=port)
        except FailedToConnectError:
            await zync_sleep(zync_mode, poll_interval)


@zyncio.zfunc
async def create_using_protocol(zync_mode: zyncio.Mode, *, client, path: str) -> SyncRpcBridge | AsyncRpcBridge:
    if not callable(getattr(client, "create_worker", None)):
        raise ValueError("No existing client supports protocol worker creation.")  # noqa: TRY004
    return await client.create_worker.z(zync_mode, path)
