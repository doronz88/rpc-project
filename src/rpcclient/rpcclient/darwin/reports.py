from pathlib import Path
from typing import List

from rpcclient.darwin.crash_reports import CrashReports


class Reports:
    """ equivalent to the data that can be found using the Console app inside the Reports section """

    def __init__(self, client, crash_reports_dir):
        self._client = client
        self.crash_reports = CrashReports(client, crash_reports_dir)

    def get_logs(self, prefix='') -> List[Path]:
        result = []
        sub_paths = ['var/log', 'Library/Logs']
        for sub_path in sub_paths:
            for path in self._client.roots:
                path = Path(path) / sub_path
                if not self._client.fs.accessible(path):
                    continue

                for root, dirs, files in self._client.fs.walk(path, onerror=lambda x: None):
                    for name in files:
                        if not self._client.fs.accessible(path):
                            continue

                        if name.endswith('.log') and name.startswith(prefix):
                            result.append(Path(root) / name)
        return result

    @property
    def system_log(self) -> str:
        with self._client.fs.open('/var/log/system.log', 'r') as f:
            return f.read().decode()
