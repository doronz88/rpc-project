import typing

from rpcclient.darwin.client import DarwinClient
from rpcclient.darwin.reports import Reports
from rpcclient.macos.apple_script import AppleScript
from rpcclient.protocol import arch_t

CRASH_REPORTS_DIR = 'Library/Logs/DiagnosticReports'


class MacosClient(DarwinClient):
    def __init__(self, sock, sysname: str, arch: arch_t, create_socket_cb: typing.Callable):
        super().__init__(sock, sysname, arch, create_socket_cb)
        self.reports = Reports(self, CRASH_REPORTS_DIR)
        self.apple_script = AppleScript(self)

    @property
    def roots(self) -> typing.List[str]:
        """ get a list of all accessible darwin roots when used for lookup of files/preferences/... """

        result = super().roots
        for username in self.fs.scandir('/Users'):
            if not username.is_dir() or not self.fs.accessible(username.path):
                continue
            result.append(username.path)
        return result
