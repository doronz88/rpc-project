import logging

import click
import coloredlogs

from client import DEFAULT_PORT, Client

coloredlogs.install(level=logging.DEBUG)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('hostname')
@click.argument('argv', nargs=-1)
@click.option('-p', '--port', type=click.INT, default=DEFAULT_PORT)
def shell(hostname, argv, port):
    if not argv:
        argv = None
    Client(hostname, port).shell(argv=argv)


if __name__ == '__main__':
    cli()
