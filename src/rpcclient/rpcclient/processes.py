from rpcclient.exceptions import BadReturnValueError
from rpcclient.structs.consts import SIGTERM


class Processes:
    def __init__(self, client):
        """
        process manager
        :param rpcclient.darwin_client.Client client: client
        """
        self._client = client

    def kill(self, pid: int, sig: int = SIGTERM):
        """ kill(pid, sig) at remote. read man for more details. """
        if 0 != self._client.symbols.kill(pid, sig):
            raise BadReturnValueError(f'kill({pid}, {sig}) failed ({self._client.last_error})')

    def waitpid(self, pid: int, flags: int = 0):
        """ waitpid(pid, sig) at remote. read man for more details. """
        with self._client.safe_malloc(8) as stat_loc:
            err = self._client.symbols.waitpid(pid, stat_loc, flags).c_int64
            if err == -1:
                raise BadReturnValueError(f'waitpid(): returned {err} ({self._client.last_error})')
            return stat_loc[0]
