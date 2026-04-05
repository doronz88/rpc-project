import logging
from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.consts import IOPMUserActiveType
from rpcclient.core._types import ClientBound
from rpcclient.core.allocated import Allocated
from rpcclient.exceptions import BadReturnValueError


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient

logger = logging.getLogger(__name__)


class PowerAssertion(Allocated["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]", identifier: int) -> None:
        self._client = client
        self.id: int = identifier

    async def _deallocate(self) -> None:
        await self._client.symbols.IOPMAssertionRelease.z(self.id)


class Power(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Power utils"""

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client

    @zyncio.zmethod
    async def declare_user_activity(self, name: str, type_: IOPMUserActiveType) -> PowerAssertion[DarwinSymbolT_co]:
        """Declares that the user is active on the system"""
        async with self._client.safe_malloc.z(8) as p_assertion_id:
            err = await self._client.symbols.IOPMAssertionDeclareUserActivity.z(
                await self._client.cf.z(name), type_, p_assertion_id
            )
            if err != 0:
                raise BadReturnValueError("IOPMAssertionCreateWithProperties() failed")
            return PowerAssertion(self._client, await p_assertion_id.getindex(0))

    @zyncio.zmethod
    async def declare_network_client_activity(self, name: str) -> PowerAssertion:
        """
        A convenience function for handling remote network clients; this is a wrapper for holding
        kIOPMAssertNetworkClientActive
        """
        async with self._client.safe_malloc.z(8) as p_assertion_id:
            err = await self._client.symbols.IOPMDeclareNetworkClientActivity.z(
                await self._client.cf.z(name), p_assertion_id
            )
            if err != 0:
                raise BadReturnValueError("IOPMAssertionCreateWithProperties() failed")
            return PowerAssertion(self._client, await p_assertion_id.getindex(0))

    @zyncio.zmethod
    async def create_assertion(self, name: str, type_: str, reason: str | None = None) -> PowerAssertion:
        properties = {"AssertName": name, "AssertType": type_}
        if reason is not None:
            properties["HumanReadableReason"] = reason
        async with self._client.safe_malloc.z(8) as p_assertion_id:
            err = await self._client.symbols.IOPMAssertionCreateWithProperties.z(
                await self._client.cf.z(properties), p_assertion_id
            )
            if err != 0:
                raise BadReturnValueError("IOPMAssertionCreateWithProperties() failed")
            return PowerAssertion(self._client, await p_assertion_id.getindex(0))

    @zyncio.zmethod
    async def copy_assertions_by_process(self) -> dict[int, dict]:
        """Returns a dictionary listing all assertions, grouped by their owning process"""
        async with self._client.safe_malloc.z(8) as p_assertions:
            if await self._client.symbols.IOPMCopyAssertionsByProcess.z(p_assertions) != 0:
                raise BadReturnValueError("IOPMCopyAssertionsByProcess() failed")
            assertions = await p_assertions.getindex(0)
        if not assertions:
            return {}
        result = {}
        key_enumerator = await assertions.objc_call.z("keyEnumerator")
        while True:
            pid_object = await key_enumerator.objc_call.z("nextObject")
            if pid_object == 0:
                break
            pid = await pid_object.py.z()
            result[pid] = await (await assertions.objc_call.z("objectForKey:", pid_object)).py.z()
        return result

    @zyncio.zmethod
    async def copy_scheduled_power_events(self) -> list[dict]:
        """List all scheduled system power events"""
        return await (await self._client.symbols.IOPMCopyScheduledPowerEvents.z()).py.z(list)

    @zyncio.zmethod
    async def copy_assertions_status(self) -> dict[str, int]:
        """Returns a list of available assertions and their system-wide levels"""
        async with self._client.safe_malloc.z(8) as result:
            if await self._client.symbols.IOPMCopyAssertionsStatus.z(result) != 0:
                raise BadReturnValueError("IOPMCopyAssertionsStatus() failed")
            return await (await result.getindex(0)).py.z(dict)

    @zyncio.zmethod
    async def reboot(self) -> None:
        if (await self._client.symbols.reboot.z()).c_int64 == -1:
            raise BadReturnValueError()

    @zyncio.zmethod
    async def sleep(self) -> None:
        """
        Enter sustem sleep

        See: https://gist.github.com/atr000/416796
        """
        async with self._client.safe_malloc.z(8) as p_master:
            err = await self._client.symbols.IOMasterPort.z(
                await self._client.symbols.bootstrap_port.getindex(0), p_master
            )
            if err != 0:
                raise BadReturnValueError(f"IOMasterPort didnt work, err is {err}")
            pmcon = await self._client.symbols.IOPMFindPowerManagement.z(await p_master.getindex(0))
            if pmcon == 0:
                raise BadReturnValueError("IOPMFindPowerManagement coudlnt establish connection")
            err = await self._client.symbols.IOPMSleepSystem.z(pmcon)
            if err != 0:
                raise BadReturnValueError(f"IOPMSleepSystem didnt work. err is {err}")
