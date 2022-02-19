from rpcclient.darwin.crash_reports import CrashReports


class Reports:
    def __init__(self, client, crash_reports_dir):
        self.crash_reports = CrashReports(client, crash_reports_dir)
