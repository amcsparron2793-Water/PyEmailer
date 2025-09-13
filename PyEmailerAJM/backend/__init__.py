from PyEmailerAJM.backend.errs import *
import warnings
import functools
from enum import IntEnum


class BasicEmailFolderChoices(IntEnum):
    INBOX = 6
    SENT_ITEMS = 5
    DRAFTS = 16
    DELETED_ITEMS = 3
    OUTBOX = 4

    def __str__(self):
        """Return the enum name as a string."""
        return self.name

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name} ({self.value})>"


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
