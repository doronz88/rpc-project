from pathlib import Path
from typing import List

from pycrashreport.crash_report import CrashReportBase, get_crash_report_from_buf


class CrashReports:
    """" manage crash reports """

    def __init__(self, client, crash_reports_dir):
        self._client = client
        self._crash_reports_dir = crash_reports_dir

    def set_symbolicated(self, enabled: bool = True):
        """
        enable/disable crash reports symbolication
        https://github.com/dlevi309/Symbolicator
        """
        self._client.preferences.cf.set('SymbolicateCrashes', enabled, 'com.apple.CrashReporter', 'root')

        # bugfix: at some point, this setting was moved to "com.apple.osanalytics" bundle identifier
        self._client.preferences.cf.set('SymbolicateCrashes', enabled, 'com.apple.osanalytics', 'root')

    def list(self, prefixed='') -> List[CrashReportBase]:
        """ get a list of all crash reports as CrashReport parsed objects """
        result = []
        for root in self._client.roots:
            root = Path(root) / self._crash_reports_dir

            if not self._client.fs.accessible(root):
                continue

            for entry in self._client.fs.scandir(root):
                if entry.is_file() and entry.name.endswith('.ips') and entry.name.startswith(prefixed):
                    with self._client.fs.open(entry.path, 'r') as f:
                        result.append(get_crash_report_from_buf(f.read().decode(), filename=entry.path))
        return result

    def clear(self, prefixed=''):
        """ remove all existing crash reports """
        for entry in self.list(prefixed=prefixed):
            self._client.fs.remove(entry.filename)
