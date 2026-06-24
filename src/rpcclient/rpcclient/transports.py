import asyncio
import logging
import os
import socket
import subprocess
import urllib.request

import requests

from rpcclient.exceptions import FailedToConnectError
from rpcclient.protocol.rpc_bridge import RpcBridge


logger = logging.getLogger(__name__)

DEFAULT_PORT = 5910
PROJECT_URL = "https://api.github.com/repos/doronz88/rpc-project/releases/latest"
BINARY_NAME = "rpcserver_macosx"


def _has_process_exited(process: subprocess.Popen) -> bool:
    return process.poll() is not None


def _terminate_process(process: subprocess.Popen) -> None:
    if _has_process_exited(process):
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


async def create_tcp(
    *,
    hostname: str | None = None,
    host: str | None = None,
    port: int = DEFAULT_PORT,
    timeout: float | None = None,
) -> RpcBridge:
    """Connect via TCP and return an `RpcBridge`."""
    target = hostname or host
    if not target:
        raise TypeError('create_tcp(): provide "hostname" or "host"')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.setblocking(False)
        await asyncio.wait_for(
            asyncio.get_running_loop().sock_connect(s, (target, port)),
            timeout,
        )
    except ConnectionRefusedError as e:
        s.close()
        raise FailedToConnectError() from e

    return await RpcBridge.connect(s)


async def create_local(
    *,
    project_url: str = PROJECT_URL,
    binary_name: str = BINARY_NAME,
    poll_interval: float = 0.1,
) -> RpcBridge:
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
    process = subprocess.Popen([f"./{binary_name}", "-p", str(port)], cwd=os.getcwd())
    logger.info("rpcserver launched on port %d", port)

    # poll until connectable
    try:
        while True:
            if _has_process_exited(process):
                raise FailedToConnectError()
            try:
                bridge = await create_tcp(hostname="127.0.0.1", port=port)
                bridge.set_local_process(process)
            except FailedToConnectError:
                await asyncio.sleep(poll_interval)
            else:
                return bridge
    except Exception:
        _terminate_process(process)
        raise


async def create_using_protocol(*, client, path: str) -> RpcBridge:
    if not callable(getattr(client, "create_worker", None)):
        raise ValueError("No existing client supports protocol worker creation.")  # noqa: TRY004
    return await client.create_worker(path)
