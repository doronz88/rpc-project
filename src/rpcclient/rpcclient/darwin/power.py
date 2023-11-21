import logging
from typing import List, Mapping

from rpcclient.darwin.consts import IOPMUserActiveType
from rpcclient.exceptions import BadReturnValueError

logger = logging.getLogger(__name__)


class PowerAssertion:
    def __init__(self, client, id: int):
        self._client = client
        self.id = id

    def __enter__(self) -> 'PowerAssertion':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._client.symbols.IOPMAssertionRelease(self.id)


class Power:
    """ Power utils """

    def __init__(self, client):
        self._client = client

    def declare_user_activity(self, name: str, type_: IOPMUserActiveType) -> PowerAssertion:
        """ Declares that the user is active on the system """
        with self._client.safe_malloc(8) as p_assertion_id:
            err = self._client.symbols.IOPMAssertionDeclareUserActivity(self._client.cf(name), type_, p_assertion_id)
            if err != 0:
                raise BadReturnValueError('IOPMAssertionCreateWithProperties() failed')
            return PowerAssertion(self._client, p_assertion_id[0])

    def declare_network_client_activity(self, name: str) -> PowerAssertion:
        """
        A convenience function for handling remote network clients; this is a wrapper for holding
        kIOPMAssertNetworkClientActive
        """
        with self._client.safe_malloc(8) as p_assertion_id:
            err = self._client.symbols.IOPMDeclareNetworkClientActivity(self._client.cf(name), p_assertion_id)
            if err != 0:
                raise BadReturnValueError('IOPMAssertionCreateWithProperties() failed')
            return PowerAssertion(self._client, p_assertion_id[0])

    def create_assertion(self, name: str, type_: str, reason: str = None) -> PowerAssertion:
        properties = {'AssertName': name, 'AssertType': type_}
        if reason is not None:
            properties['HumanReadableReason'] = reason
        with self._client.safe_malloc(8) as p_assertion_id:
            err = self._client.symbols.IOPMAssertionCreateWithProperties(self._client.cf(properties), p_assertion_id)
            if err != 0:
                raise BadReturnValueError('IOPMAssertionCreateWithProperties() failed')
            return PowerAssertion(self._client, p_assertion_id[0])

    def copy_assertions_by_process(self) -> Mapping[int, Mapping]:
        """ Returns a dictionary listing all assertions, grouped by their owning process """
        with self._client.safe_malloc(8) as p_assertions:
            if self._client.symbols.IOPMCopyAssertionsByProcess(p_assertions) != 0:
                raise BadReturnValueError('IOPMCopyAssertionsByProcess() failed')
            assertions = p_assertions[0]
        if not assertions:
            return {}
        result = {}
        key_enumerator = assertions.objc_call('keyEnumerator')
        while True:
            pid_object = key_enumerator.objc_call('nextObject')
            if pid_object == 0:
                break
            pid = pid_object.py()
            result[pid] = assertions.objc_call('objectForKey:', pid_object).py()
        return result

    def copy_scheduled_power_events(self) -> List[Mapping]:
        """ List all scheduled system power events """
        return self._client.symbols.IOPMCopyScheduledPowerEvents().py()

    def copy_assertions_status(self) -> Mapping[str, int]:
        """ Returns a list of available assertions and their system-wide levels """
        with self._client.safe_malloc(8) as result:
            if 0 != self._client.symbols.IOPMCopyAssertionsStatus(result):
                raise BadReturnValueError('IOPMCopyAssertionsStatus() failed')
            return result[0].py()

    def reboot(self) -> None:
        if self._client.symbols.reboot().c_int64 == -1:
            raise BadReturnValueError()

    def sleep(self) -> None:
        """
        Enter sustem sleep

        See: https://gist.github.com/atr000/416796
        """
        with self._client.safe_malloc(8) as p_master:
            err = self._client.symbols.IOMasterPort(self._client.symbols.bootstrap_port[0], p_master)
            if err != 0:
                raise BadReturnValueError(f'IOMasterPort didnt work, err is {err}')
            pmcon = self._client.symbols.IOPMFindPowerManagement(p_master[0])
            if pmcon == 0:
                raise BadReturnValueError('IOPMFindPowerManagement coudlnt establish connection')
            err = self._client.symbols.IOPMSleepSystem(pmcon)
            if err != 0:
                raise BadReturnValueError(f'IOPMSleepSystem didnt work. err is {err}')
