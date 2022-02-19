from rpcclient.darwin.crash_reports import CrashReports


class Reports:
    """ equivalent to the data that can be found using the Console app inside the Reports section """

    def __init__(self, client, crash_reports_dir):
        self._client = client
        self.crash_reports = CrashReports(client, crash_reports_dir)

    @property
    def system_log(self) -> str:
        with self._client.fs.open('/var/log/system.log', 'r') as f:
            return f.readall().decode()
