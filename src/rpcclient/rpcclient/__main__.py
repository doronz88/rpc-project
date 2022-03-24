import logging

import click
import coloredlogs

from rpcclient.client_factory import create_client
from rpcclient.protocol import DEFAULT_PORT

coloredlogs.install(level=logging.DEBUG)

logging.getLogger('asyncio').disabled = True
logging.getLogger('parso').disabled = True
logging.getLogger('parso.cache').disabled = True
logging.getLogger('parso.python.diff').disabled = True
logging.getLogger('blib2to3.pgen2.driver').disabled = True
logging.getLogger('PIL.PngImagePlugin').disabled = True


@click.command()
@click.argument('hostname')
@click.option('-p', '--port', type=click.INT, default=DEFAULT_PORT)
def cli(hostname, port):
    create_client(hostname, port=port).interactive()


if __name__ == '__main__':
    cli()
