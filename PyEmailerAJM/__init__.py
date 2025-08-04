from PyEmailerAJM.PyEmailerAJM import PyEmailer
from PyEmailerAJM.PyEmailerAJM import EmailerNotSetupError
from PyEmailerAJM.PyEmailerAJM import DisplayManualQuit

import warnings
import functools


def deprecated(reason: str = ""):
    """
    Decorator that marks a function or method as deprecated.

    :param reason: Optional message to explain what to use instead
                   or when the feature will be removed.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            message = f"Function '{func.__name__}' is deprecated."
            if reason:
                message += f" {reason}"
            warnings.warn(message, category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator
