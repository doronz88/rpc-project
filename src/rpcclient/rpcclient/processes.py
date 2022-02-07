from rpcclient.exceptions import BadReturnValueError


class Processes:
    def __init__(self, client):
        """
        process manager
        :param rpcclient.darwin_client.Client client: client
        """
        self._client = client

    def kill(self, pid: int, sig: int):
        """ kill(pid, sig) at remote. read man for more details. """
        return self._client.kill(pid, sig)

    def waitpid(self, pid: int):
        """ waitpid(pid, sig) at remote. read man for more details. """
        with self._client.safe_malloc(8) as stat_loc:
            err = self._client.symbols.waitpid(pid, stat_loc, 0)
            if err:
                raise BadReturnValueError(f'waitpid(): returned {err}')
            return stat_loc[0]
