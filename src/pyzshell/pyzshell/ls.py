import sys
import posixpath

from pygnuutils.ls import LsStub


class Ls(LsStub):
    def __init__(self, client):
        self._client = client

    @property
    def sep(self):
        return posixpath.sep

    def join(self, path, *paths):
        return posixpath.join(path, *paths)

    def abspath(self, path):
        return posixpath.normpath(path)

    def stat(self, path, dir_fd=None, follow_symlinks=True):
        return self._client.stat(path)

    def readlink(self, path, dir_fd=None):
        return self._client.readlink(path)

    def isabs(self, path):
        return posixpath.isabs(path)

    def dirname(self, path):
        return posixpath.dirname(path)

    def basename(self, path):
        return posixpath.basename(path)

    def getgroup(self, st_gid):
        return '-'

    def getuser(self, st_uid):
        return '-'

    def now(self):
        return '-'

    def listdir(self, path='.'):
        return self._client.listdir(path)

    def system(self):
        return self._client.os_family

    def getenv(self, key, default=None):
        return ''

    def print(self, *objects, sep=' ', end='\n', file=sys.stdout, flush=False):
        print(objects[0], end=end)
