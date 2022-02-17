class RpcClientException(Exception):
    pass


class InvalidServerVersionMagicError(RpcClientException):
    pass


class ServerDiedError(RpcClientException):
    pass


class SymbolAbsentError(RpcClientException):
    pass


class ArgumentError(RpcClientException):
    pass


class BadReturnValueError(RpcClientException):
    pass


class NoSuchPreferenceError(RpcClientException):
    pass


class CfSerializationError(RpcClientException):
    pass


class SpawnError(RpcClientException):
    pass


class InvalidArgumentError(RpcClientException):
    pass


class FailedToConnectError(RpcClientException):
    pass


class UnrecognizedSelectorError(RpcClientException):
    pass


class GettingObjectiveCClassError(RpcClientException):
    pass


class MissingLibraryError(RpcClientException):
    pass


class PermissionDeniedError(RpcClientException):
    pass
