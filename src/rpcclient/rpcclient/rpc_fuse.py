import logging

import click
import coloredlogs

import fuse
from fuse import Fuse

from rpcclient.client_factory import create_client
from rpcclient.fs import File
from rpcclient.protocol import DEFAULT_PORT
from rpcclient.structs.consts import EACCESS

coloredlogs.install(level=logging.DEBUG)

logging.getLogger('asyncio').disabled = True
logging.getLogger('parso').disabled = True
logging.getLogger('parso.cache').disabled = True
logging.getLogger('parso.python.diff').disabled = True
logging.getLogger('blib2to3.pgen2.driver').disabled = True
logging.getLogger('humanfriendly.prompts').disabled = True

if not hasattr(fuse, '__version__'):
    raise RuntimeError("your fuse-py doesn't know of fuse.__version__, probably it's too old.")

fuse.fuse_python_api = (0, 2)

logger = logging.getLogger()
handler = logging.FileHandler('/tmp/logfile.log')
logger.addHandler(handler)


class RpcFs(Fuse):
    client = None

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.file_class = RpcFile
        logger.debug('RpcFs init called')

    def getattr(self, path: str):
        logger.debug('getattr')
        return self.client.fs.lstat(path)

    def readlink(self, path: str):
        logger.debug('readlink')
        return self.client.fs.readlink(path, absolute=False)

    def readdir(self, path: str, offset: int):
        logger.debug('readdir')
        for file in self.client.fs.listdir(path):
            yield fuse.Direntry(file)

    def unlink(self, path: str):
        logger.debug('unlink')
        self.client.fs.remove(path)

    def rmdir(self, path: str):
        logger.debug('rmdir')
        self.client.fs.remove(path)

    def symlink(self, path: str, path1: str):
        logger.debug('symlink')
        self.client.fs.symlink(path, path1)

    def rename(self, path: str, path1: str):
        logger.debug('rename')
        self.client.fs.rename(path, path1)

    def link(self, path: str, path1: str):
        logger.debug('link')
        self.client.fs.link(path, path1)

    def chmod(self, path: str, mode: int):
        logger.debug('chmod')
        self.client.fs.chmod(path, mode)

    def chown(self, path: str, uid: int, gid: int):
        logger.debug('chown')
        self.client.fs.chown(path, uid, gid)

    def mkdir(self, path: str):
        logger.debug('mkdir')
        self.client.fs.mkdir(path)

    def access(self, path: str, mode: int):
        logger.debug(f'access {path} {mode}')
        if 0 != self.client.symbols.access(path, mode):
            logger.debug('denied')
            return -EACCESS
        logger.debug('granted')

    def fsinit(self):
        logger.debug('fsinit')
        self.client.fs.chdir('/')


class RpcFile:
    client = None

    def __init__(self, path: str, flags: int, *mode):
        logger.debug('RpcFile ctor')
        fd = self.client.symbols.open(path, flags, *mode)
        if fd < 0:
            raise self.client.raise_errno_exception(f'open() failed for: {path}')
        self.file = File(self.client, fd)
        logger.debug('RpcFile ctor done')

    def read(self, length, offset):
        logger.debug('read')
        return self.file.pread(length, offset)

    def write(self, buf, offset):
        logger.debug('write')
        self.file.pwrite(buf, offset)

    def release(self, flags):
        self.file.deallocate()

    def _fflush(self):
        pass

    def fsync(self, isfsyncfile):
        self._fflush()
        if isfsyncfile:
            self.file.fdatasync()
        else:
            self.file.fsync()

    def flush(self):
        self._fflush()
        self.client.symbols.close(self.file.dup())

    # def fgetattr(self):
    #     return os.fstat(self.fd)

    # def ftruncate(self, len):
    #     self.file.truncate(len)

    # def lock(self, cmd, owner, **kw):
    #     pass


@click.command()
@click.argument('hostname')
@click.argument('mount_point')
@click.option('-p', '--port', type=click.INT, default=DEFAULT_PORT)
def cli(hostname, mount_point, port):
    RpcFs.client = create_client(hostname, port=port)
    RpcFile.client = create_client(hostname, port=port)
    server = RpcFs(version="%prog " + fuse.__version__, dash_s_do='setsingle')
    server.fuse_args.mountpoint = mount_point
    server.main()


if __name__ == '__main__':
    cli()
