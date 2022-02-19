from typing import List

from pycrashreport.crash_report import CrashReport


class CrashReports:
    def __init__(self, client, crash_reports_dir):
        self._client = client
        self._crash_reports_dir = crash_reports_dir

    def list(self, prefixed='') -> List[CrashReport]:
        result = []
        for entry in self._client.fs.scandir(self._crash_reports_dir):
            if entry.is_file() and entry.name.endswith('.ips') and entry.name.startswith(prefixed):
                with self._client.fs.open(entry.path, 'r') as f:
                    result.append(CrashReport(f.readall().decode(), filename=entry.path))
        return result

    def clear(self, prefixed=''):
        for entry in self._client.fs.scandir(self._crash_reports_dir):
            if entry.is_file() and entry.name.endswith('.ips') and entry.name.startswith(prefixed):
                self._client.fs.remove(entry.path)
