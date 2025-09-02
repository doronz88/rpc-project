from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.clients.darwin.subsystems.reports import Reports
from rpcclient.clients.macos.subsystems.apple_script import AppleScript
from rpcclient.core.subsystems.decorator import subsystem

CRASH_REPORTS_DIR = 'Library/Logs/DiagnosticReports'


class MacosClient(DarwinClient):

    @subsystem
    def reports(self) -> Reports:
        return Reports(self, CRASH_REPORTS_DIR)

    @subsystem
    def apple_script(self) -> AppleScript:
        return AppleScript(self)

    @property
    def roots(self) -> list[str]:
        """ get a list of all accessible darwin roots when used for lookup of files/preferences/... """

        result = super().roots
        for username in self.fs.scandir('/Users'):
            if not username.is_dir() or not self.fs.accessible(username.path):
                continue
            result.append(username.path)
        return result
