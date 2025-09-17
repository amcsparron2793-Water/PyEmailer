from PyEmailerAJM.backend.errs import *
from PyEmailerAJM.backend.enums import BasicEmailFolderChoices, AlertTypes
from PyEmailerAJM.backend.the_sandman import TheSandman
from PyEmailerAJM.backend.email_state import EmailState
from PyEmailerAJM.backend.snooze_tracking import SnoozeTracking
from PyEmailerAJM.backend.continuous_colorizer import ContinuousColorizer
from PyEmailerAJM.backend.logger import PyEmailerLogger
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
