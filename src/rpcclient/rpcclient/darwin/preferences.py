from rpcclient.darwin.cfpreferences import CFPreferences
from rpcclient.darwin.scpreferences import SCPreferences


class Preferences:
    """ Preferences utils """

    def __init__(self, client):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self.cf = CFPreferences(client)
        self.sc = SCPreferences(client)
