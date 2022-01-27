import logging
import sys

import IPython
import click
import coloredlogs

from client import DEFAULT_PORT, Client

coloredlogs.install(level=logging.DEBUG)

logging.getLogger('asyncio').disabled = True
logging.getLogger('parso').disabled = True
logging.getLogger('parso.cache').disabled = True


@click.group()
@click.argument('hostname')
@click.option('-p', '--port', type=click.INT, default=DEFAULT_PORT)
@click.pass_context
def cli(ctx, hostname, port):
    ctx.ensure_object(dict)
    ctx.obj['client'] = Client(hostname, port=port)


@cli.command()
@click.argument('argv', nargs=-1)
@click.pass_context
def shell(ctx, argv):
    if not argv:
        argv = None
    ctx.obj['client'].shell(argv=argv)


@cli.command()
@click.argument('src')
@click.argument('dst', required=False)
@click.pass_context
def pull(ctx, src, dst):
    buf = ctx.obj['client'].get_file(src)
    if dst:
        with open(dst, 'wb') as f:
            f.write(buf)
    else:
        sys.stdout.write(buf.decode())


@cli.command()
@click.argument('src', type=click.File('rb'))
@click.argument('dst')
@click.pass_context
def push(ctx, src, dst):
    ctx.obj['client'].put_file(dst, src.read())


@cli.command()
@click.pass_context
def ishell(ctx):
    client = ctx.obj['client']
    IPython.embed()


if __name__ == '__main__':
    cli()
