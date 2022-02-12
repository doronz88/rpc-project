class RpcClientException(Exception):
    pass


class SymbolAbsentError(RpcClientException):
    pass


class ArgumentError(RpcClientException):
    pass


class BadReturnValueError(RpcClientException):
    pass


class NoSuchPreference(RpcClientException):
    pass


class CfSerializationError(RpcClientException):
    pass


class SpawnError(RpcClientException):
    pass


class InvalidArgumentError(RpcClientException):
    pass


class FailedToConnectError(RpcClientException):
    pass


class UnrecognizedSelector(RpcClientException):
    pass
