from rpcclient.clients.darwin.subsystems.cfpreferences import CFPreferences
from rpcclient.clients.darwin.subsystems.scpreferences import SCPreferences


class Preferences:
    """ Preferences utils """

    def __init__(self, client):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self.cf = CFPreferences(client)
        self.sc = SCPreferences(client)
