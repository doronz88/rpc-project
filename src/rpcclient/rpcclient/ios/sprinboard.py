from rpcclient.exceptions import RpcFailedLaunchingAppError


class SpringBoard:
    def __init__(self, client):
        self._client = client

    def launch_application(self, bundle_identifier: str) -> None:
        """ launch application using SpringBoardServices """
        err = self._client.symbols.SBSLaunchApplicationWithIdentifier(self._client.cf(bundle_identifier), 0)
        if err != 0:
            raise RpcFailedLaunchingAppError(err)
