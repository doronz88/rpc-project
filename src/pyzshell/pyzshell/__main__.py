import logging
import sys

import click
import coloredlogs

from pyzshell.client import DEFAULT_PORT, Client

coloredlogs.install(level=logging.DEBUG)

logging.getLogger('asyncio').disabled = True
logging.getLogger('parso').disabled = True
logging.getLogger('parso.cache').disabled = True
logging.getLogger('parso.python.diff').disabled = True


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
    ctx.obj['client'].spawn(argv=argv)


@cli.command()
@click.argument('src')
@click.argument('dst', required=False)
@click.pass_context
def pull(ctx, src, dst):
    buf = ctx.obj['client'].fs.read_file(src)
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
    ctx.obj['client'].fs.write_file(dst, src.read())


@cli.command()
@click.pass_context
def ishell(ctx):
    ctx.obj['client'].interactive()


if __name__ == '__main__':
    cli()
