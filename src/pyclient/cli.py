import logging
import sys

import click
import coloredlogs

from client import DEFAULT_PORT, Client

coloredlogs.install(level=logging.DEBUG)


def connection_params(func):
    return click.argument('hostname')(click.option('-p', '--port', type=click.INT, default=DEFAULT_PORT)(func))


@click.group()
def cli():
    pass


@cli.command()
@connection_params
@click.argument('argv', nargs=-1)
def shell(hostname, port, argv):
    if not argv:
        argv = None
    Client(hostname, port).shell(argv=argv)


@cli.command()
@connection_params
@click.argument('src')
@click.argument('dst', required=False)
def pull(hostname, port, src, dst):
    buf = Client(hostname, port).get_file(src)
    if dst:
        with open(dst, 'wb') as f:
            f.write(buf)
    else:
        sys.stdout.write(buf.decode())


if __name__ == '__main__':
    cli()
