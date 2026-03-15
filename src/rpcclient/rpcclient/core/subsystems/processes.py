import zyncio

from rpcclient.core._types import ClientBound, ClientT_co
from rpcclient.core.structs.consts import SIGTERM
from rpcclient.exceptions import BadReturnValueError


class Processes(ClientBound[ClientT_co]):
    def __init__(self, client: ClientT_co) -> None:
        """
        process manager
        :param rpcclient.darwin_client.Client client: client
        """
        self._client = client

    @zyncio.zmethod
    async def kill(self, pid: int, sig: int = SIGTERM) -> None:
        """Send a signal to a remote process."""
        if await self._client.symbols.kill.z(pid, sig) != 0:
            raise BadReturnValueError(f"kill({pid}, {sig}) failed ({await self._client.get_last_error.z()})")

    @zyncio.zmethod
    async def waitpid(self, pid: int, flags: int = 0) -> int:
        """Wait for a remote process to change state and return status."""
        async with self._client.safe_malloc.z(8) as stat_loc:
            err = (await self._client.symbols.waitpid.z(pid, stat_loc, flags)).c_int64
            if err == -1:
                raise BadReturnValueError(f"waitpid(): returned {err} ({await self._client.get_last_error.z()})")
            return int(await stat_loc.getindex(0))
