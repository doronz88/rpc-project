from functools import wraps
import os
import inspect


def path_to_str(*params):
    """
    Decorator for converting parameters to string.
    :param params: List of parameters names to convert.
    """

    def decorate_func(f):
        @wraps(f)
        def new_f(*args, **kwargs):
            try:
                ba = inspect.signature(f).bind(*args, **kwargs)
            except TypeError:
                # Binding failed, let the original function traceback rise.
                pass
            else:
                for param in params:
                    ba.arguments[param] = str(ba.arguments[param])
                return f(*ba.args, **ba.kwargs)
            return f(*args, **kwargs)

        signature = inspect.signature(f)
        new_params = {k: v for k, v in signature.parameters.items()}
        for p in params:
            new_params[p] = signature.parameters[p].replace(annotation=os.PathLike)
        new_f.__signature__ = signature.replace(parameters=list(new_params.values()))

        return new_f

    return decorate_func
