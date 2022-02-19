from rpcclient.darwin.client import DarwinClient
from rpcclient.macos.bluetooth import Bluetooth
from rpcclient.darwin.reports import Reports

CRASH_REPORTS_DIR = '/Library/Logs/DiagnosticReports'


class MacosClient(DarwinClient):

    def __init__(self, sock, sysname: str, hostname: str, port: int = None):
        super().__init__(sock, sysname, hostname, port)
        self.bluetooth = Bluetooth(self)
        self.crash_reports = Reports(self, CRASH_REPORTS_DIR)
