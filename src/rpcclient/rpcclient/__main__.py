import logging

import click
import coloredlogs

from rpcclient.client_factory import create_tcp_client
from rpcclient.protocol import DEFAULT_PORT

coloredlogs.install(level=logging.DEBUG)

logging.getLogger('asyncio').disabled = True
logging.getLogger('parso').disabled = True
logging.getLogger('parso.cache').disabled = True
logging.getLogger('parso.python.diff').disabled = True
logging.getLogger('blib2to3.pgen2.driver').disabled = True
logging.getLogger('humanfriendly.prompts').disabled = True


@click.command()
@click.argument('hostname')
@click.option('-p', '--port', type=click.INT, default=DEFAULT_PORT)
@click.option('-r', '--rebind-symbols', is_flag=True, help='reload all symbols upon connection')
@click.option('-l', '--load-all-libraries', is_flag=True, help='load all libraries')
def cli(hostname: str, port: int, rebind_symbols: bool, load_all_libraries: bool):
    client = create_tcp_client(hostname, port=port)
    if load_all_libraries:
        client.load_all_libraries(rebind_symbols=False)
    if rebind_symbols:
        client.rebind_symbols()
    client.interactive()


if __name__ == '__main__':
    cli()
