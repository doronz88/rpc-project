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


class ProcessSymbolAbsentError(RpcClientException):
    """ trying to access a symbol which is not exported from any library currently loaded into the process's memory """
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
    """ failed to encode/decode a cfobject into/from a python object """
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


class NoEntitlementsError(RpcClientException):
    """ binary contains no entitlements """
    pass


class HarGlobalNotFoundError(RpcClientException):
    """ Failed to find Harlogger global """
    pass


class ElementNotFoundError(RpcClientException):
    """ Failed to find element """
    pass


class FirstElementNotFoundError(ElementNotFoundError):
    """ Failed to find the first element """
    pass


class LastElementNotFoundError(ElementNotFoundError):
    """ Failed to find the last element """
    pass


class RpcFileExistsError(BadReturnValueError):
    """ RPC version for FileExistsError (errno = EEXIST) """
    pass


class RpcFileNotFoundError(BadReturnValueError):
    """ RPC version for FileNotFoundError (errno = ENOENTRY) """
    pass


class RpcBrokenPipeError(BadReturnValueError):
    """ RPC version for BrokenPipeError (errno = EPIPE) """
    pass


class RpcNotEmptyError(BadReturnValueError):
    """ raised when errno = ENOTEMPTY """
    pass


class RpcIsADirectoryError(BadReturnValueError):
    """ RPC version for IsADirectoryError (errno = ENOTEMPTY) """
    pass


class RpcNotADirectoryError(BadReturnValueError):
    """ RPC version for NotADirectoryError (errno = ENOTDIR) """
    pass


class RpcPermissionError(BadReturnValueError):
    """ RPC version for PermissionError (errno = EPERM) """
    pass


class RpcAccessibilityTurnedOffError(BadReturnValueError):
    """ Application AX and Automation is turned off """
    pass


class RpcFailedToRecordError(BadReturnValueError):
    """ An attempt to record has failed """
    pass


class RpcFailedToPlayError(BadReturnValueError):
    """ An attempt to play has failed """
    pass


class RpcResourceTemporarilyUnavailableError(BadReturnValueError):
    """ raised when errno = EAGAIN """
    pass


class RpcConnectionRefusedError(BadReturnValueError):
    """ RPC version for ConnectionRefusedError (errno = ECONNREFUSED) """
    pass


class NoSuchActivityError(RpcClientException):
    pass


class RpcFailedLaunchingAppError(BadReturnValueError):
    """ Failed to launch application """
    pass


class RpcAppleScriptError(BadReturnValueError):
    """ Failed to execute given AppleScript """
    pass


class RpcXpcError(BadReturnValueError):
    """ XPC-related error """
    pass


class RpcXpcSerializationError(RpcXpcError):
    """ Failed to serialize/deserialize XPC message """
    pass


class RpcSetDeveloperModeError(BadReturnValueError):
    """ Failed to set Developer Mode """
    pass
