import logging
from typing import Union

import click
import coloredlogs

from rpcclient.client_manager import ClientManager
from rpcclient.console.console import Console, disable_loggers
from rpcclient.transports import DEFAULT_PORT

coloredlogs.install(level=logging.DEBUG)

disable_loggers()


@click.command()
def rpclocal() -> None:
    """ connect to a local machine """
    manager = ClientManager()
    client = manager.create(mode='local')
    Console(manager).interactive(switch_cid=client.id)


@click.command()
@click.argument('hostname', required=False)
@click.option('-p', '--port', type=click.INT, default=DEFAULT_PORT, help='TCP port to connect to')
@click.option('-r', '--rebind-symbols', is_flag=True, help='reload all symbols upon connection')
@click.option('-l', '--load-all-libraries', is_flag=True, help='load all libraries')
def rpcclient(hostname: Union[str, None], port: int, rebind_symbols: bool, load_all_libraries: bool):
    """
    Start the console.
    If HOSTNAME is provided, connect immediately.
    Otherwise, start without a connection.
    You can connect later from the console.
    """
    manager = ClientManager()
    cid = None
    if hostname:
        client = manager.create(hostname=hostname, port=port)
        cid = client.id
        if rebind_symbols:
            client.rebind_symbols()
        if load_all_libraries:
            client.load_all_libraries()

    Console(manager).interactive(switch_cid=cid)


if __name__ == '__main__':
    rpcclient()
