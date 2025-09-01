import logging
import os
import subprocess
import time
import urllib.request
from socket import socket
from typing import Union

import requests

from rpcclient.core.protosocket import ProtoSocket
from rpcclient.exceptions import FailedToConnectError

logger = logging.getLogger(__name__)

DEFAULT_PORT = 5910
PROJECT_URL = "https://api.github.com/repos/doronz88/rpc-project/releases/latest"
BINARY_NAME = "rpcserver_macosx"


def create_tcp(*, hostname: Union[str, None] = None, host: Union[str, None] = None,
               port: int = DEFAULT_PORT, timeout: Union[float, None] = None) -> ProtoSocket:
    """ Connect via TCP and return a ProtoSocket. """
    target = hostname or host
    if not target:
        raise TypeError('tcp(): provide "hostname" or "host"')
    s = socket()
    if timeout is not None:
        s.settimeout(timeout)
    try:
        s.connect((target, port))
    except ConnectionRefusedError as e:
        s.close()
        raise FailedToConnectError() from e
    return ProtoSocket(s)


def create_local(*, project_url: str = PROJECT_URL, binary_name: str = BINARY_NAME,
                 poll_interval: float = 0.1) -> ProtoSocket:
    """
    Download the latest rpcserver release asset, spawn it locally on a free port,
    and connect via TCP. Returns a ProtoSocket.
    """
    resp = requests.get(project_url)
    resp.raise_for_status()
    for asset in resp.json().get('assets', []):
        if asset.get('name') == binary_name:
            url = asset['browser_download_url']
            logger.info('Downloading %s from %s', binary_name, url)
            urllib.request.urlretrieve(url, binary_name)
            os.chmod(binary_name, os.stat(binary_name).st_mode | 0o100)
            break

    # pick a free port
    srv = socket()
    srv.bind(('127.0.0.1', 0))
    port = srv.getsockname()[1]
    srv.close()

    # spawn
    subprocess.Popen([f'./{binary_name}', '-p', str(port)], cwd=os.getcwd())
    logger.info('rpcserver launched on port %d', port)

    # poll until connectable
    while True:
        try:
            return create_tcp(hostname='127.0.0.1', port=port)
        except FailedToConnectError:
            time.sleep(poll_interval)
