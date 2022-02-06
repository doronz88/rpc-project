class ZShellError(Exception):
    pass


class SymbolAbsentError(ZShellError):
    pass


class ArgumentError(ZShellError):
    pass


class BadReturnValueError(ZShellError):
    pass


class NoSuchPreference(ZShellError):
    pass


class CfSerializationError(ZShellError):
    pass


class SpawnError(ZShellError):
    pass


class InvalidArgumentError(ZShellError):
    pass


class FailedToConnectError(ZShellError):
    pass
