import typing

from rpcclient.darwin.client import DarwinClient
from rpcclient.darwin.reports import Reports

CRASH_REPORTS_DIR = 'Library/Logs/DiagnosticReports'


class MacosClient(DarwinClient):

    def __init__(self, sock, sysname: str, hostname: str, port: int = None):
        super().__init__(sock, sysname, hostname, port)
        self.reports = Reports(self, CRASH_REPORTS_DIR)

    @property
    def roots(self) -> typing.List[str]:
        """ get a list of all accessible darwin roots when used for lookup of files/preferences/... """

        result = super().roots
        for username in self.fs.scandir('/Users'):
            if not username.is_dir() or not self.fs.accessible(username.path):
                continue
            result.append(username.path)
        return result
