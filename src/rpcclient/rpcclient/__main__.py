import logging

import click
import coloredlogs

from rpcclient.client_manager import ClientManager
from rpcclient.clients.darwin.client import BaseDarwinClient
from rpcclient.console.console import Console, disable_loggers
from rpcclient.transports import DEFAULT_PORT


coloredlogs.install(level=logging.DEBUG)

disable_loggers()

startup_files_option = click.option(
    "-f",
    "--startup-files",
    type=click.Path(exists=True),
    multiple=True,
    help="File(s) (python) to run on session start. Multiple files can be provided.",
)


@click.command()
@startup_files_option
def rpclocal(startup_files: tuple[str]) -> None:
    """connect to a local machine"""
    manager = ClientManager()
    client = manager.create(mode="local")

    Console(manager).interactive(switch_cid=client.id, startup_files=startup_files)


@click.command()
@click.argument("hostname", required=False)
@click.option("-p", "--port", type=click.INT, default=DEFAULT_PORT, help="TCP port to connect to")
@click.option("-r", "--rebind-symbols", is_flag=True, help="reload all symbols upon connection")
@click.option("-l", "--load-all-libraries", is_flag=True, help="load all libraries")
@startup_files_option
def rpcclient(
    hostname: str | None, port: int, rebind_symbols: bool, load_all_libraries: bool, startup_files: tuple[str]
):
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
        if isinstance(client, BaseDarwinClient):
            if rebind_symbols:
                client.rebind_symbols()
            if load_all_libraries:
                client.load_all_libraries()

    Console(manager).interactive(switch_cid=cid, startup_files=startup_files)


if __name__ == "__main__":
    rpcclient()
