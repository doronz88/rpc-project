class RpcClientException(Exception):
    """ general exception """
    pass


class InvalidServerVersionMagicError(RpcClientException):
    """ server handshake failed due to an invalid magic """
    pass


class ServerDiedError(RpcClientException):
    """ server became disconnected during an operation """
    pass


class SymbolAbsentError(RpcClientException):
    """ trying to access a symbol which is not exported from any library currently loaded into the server's memory """
    pass


class ArgumentError(RpcClientException):
    """ at least one of the supplied arguments for a given function was invalid """
    pass


class BadReturnValueError(RpcClientException):
    """ remote c function returned an error """
    pass


class NoSuchPreferenceError(RpcClientException):
    """ attempt to read a preference data which doesn't exist """
    pass


class CfSerializationError(RpcClientException):
    """ failed to decode a cfobject into a python object """
    pass


class SpawnError(RpcClientException):
    """ failed to spawn a child process """
    pass


class FailedToConnectError(RpcClientException):
    """ failed to connect to rpcserver """
    pass


class UnrecognizedSelectorError(RpcClientException):
    """ tried to access a non-existing objc object selector """
    pass


class GettingObjectiveCClassError(RpcClientException):
    """ failed to create an objc class wrapper for a given object """
    pass


class MissingLibraryError(RpcClientException):
    """ a required library could not be found """
    pass


class PermissionDeniedError(RpcClientException):
    """ failed to access a certain something """
    pass


class NoEntitlementsError(RpcClientException):
    """ binary contains no entitlements """
    pass


class ElementNotFoundError(RpcClientException):
    """ Failed to find element """
    pass
