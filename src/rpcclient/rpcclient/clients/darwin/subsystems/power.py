import logging
from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.consts import IOPMUserActiveType
from rpcclient.core._types import ClientBound
from rpcclient.core.allocated import Allocated
from rpcclient.exceptions import BadReturnValueError


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient

logger = logging.getLogger(__name__)


class PowerAssertion(Allocated["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]", identifier: int) -> None:
        self._client = client
        self.id: int = identifier

    async def _deallocate(self) -> None:
        await self._client.symbols.IOPMAssertionRelease(self.id)


class Power(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Power utils"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client

    async def declare_user_activity(self, name: str, type_: IOPMUserActiveType) -> PowerAssertion[DarwinSymbolT_co]:
        """Declares that the user is active on the system"""
        async with self._client.safe_malloc(8) as p_assertion_id:
            err = await self._client.symbols.IOPMAssertionDeclareUserActivity(
                await self._client.cf(name), type_, p_assertion_id
            )
            if err != 0:
                raise BadReturnValueError("IOPMAssertionCreateWithProperties() failed")
            return PowerAssertion(self._client, await p_assertion_id.getindex(0))

    async def declare_network_client_activity(self, name: str) -> PowerAssertion:
        """
        A convenience function for handling remote network clients; this is a wrapper for holding
        kIOPMAssertNetworkClientActive
        """
        async with self._client.safe_malloc(8) as p_assertion_id:
            err = await self._client.symbols.IOPMDeclareNetworkClientActivity(
                await self._client.cf(name), p_assertion_id
            )
            if err != 0:
                raise BadReturnValueError("IOPMAssertionCreateWithProperties() failed")
            return PowerAssertion(self._client, await p_assertion_id.getindex(0))

    async def create_assertion(self, name: str, type_: str, reason: str | None = None) -> PowerAssertion:
        properties = {"AssertName": name, "AssertType": type_}
        if reason is not None:
            properties["HumanReadableReason"] = reason
        async with self._client.safe_malloc(8) as p_assertion_id:
            err = await self._client.symbols.IOPMAssertionCreateWithProperties(
                await self._client.cf(properties), p_assertion_id
            )
            if err != 0:
                raise BadReturnValueError("IOPMAssertionCreateWithProperties() failed")
            return PowerAssertion(self._client, await p_assertion_id.getindex(0))

    async def copy_assertions_by_process(self) -> dict[int, dict]:
        """Returns a dictionary listing all assertions, grouped by their owning process"""
        async with self._client.safe_malloc(8) as p_assertions:
            if await self._client.symbols.IOPMCopyAssertionsByProcess(p_assertions) != 0:
                raise BadReturnValueError("IOPMCopyAssertionsByProcess() failed")
            assertions = await p_assertions.getindex(0)
        if not assertions:
            return {}
        result = {}
        key_enumerator = await assertions.objc_call("keyEnumerator")
        while True:
            pid_object = await key_enumerator.objc_call("nextObject")
            if pid_object == 0:
                break
            pid = await pid_object.py()
            result[pid] = await (await assertions.objc_call("objectForKey:", pid_object)).py()
        return result

    async def copy_scheduled_power_events(self) -> list[dict]:
        """List all scheduled system power events"""
        return await (await self._client.symbols.IOPMCopyScheduledPowerEvents()).py(list)

    async def copy_assertions_status(self) -> dict[str, int]:
        """Returns a list of available assertions and their system-wide levels"""
        async with self._client.safe_malloc(8) as result:
            if await self._client.symbols.IOPMCopyAssertionsStatus(result) != 0:
                raise BadReturnValueError("IOPMCopyAssertionsStatus() failed")
            return await (await result.getindex(0)).py(dict)

    async def reboot(self) -> None:
        if (await self._client.symbols.reboot()).c_int64 == -1:
            raise BadReturnValueError()

    async def sleep(self) -> None:
        """
        Enter sustem sleep

        See: https://gist.github.com/atr000/416796
        """
        async with self._client.safe_malloc(8) as p_master:
            err = await self._client.symbols.IOMasterPort(
                await self._client.symbols.bootstrap_port.getindex(0), p_master
            )
            if err != 0:
                raise BadReturnValueError(f"IOMasterPort didnt work, err is {err}")
            pmcon = await self._client.symbols.IOPMFindPowerManagement(await p_master.getindex(0))
            if pmcon == 0:
                raise BadReturnValueError("IOPMFindPowerManagement coudlnt establish connection")
            err = await self._client.symbols.IOPMSleepSystem(pmcon)
            if err != 0:
                raise BadReturnValueError(f"IOPMSleepSystem didnt work. err is {err}")
