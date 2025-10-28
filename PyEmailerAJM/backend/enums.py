from enum import Enum, IntEnum


class AlertTypes(Enum):
    """
    An enumeration to represent different alert types with associated integer values.

    Attributes:
        WARNING: An alert type indicating a warning with an associated value of 5.
        CRITICAL_WARNING: An alert type indicating a critical warning with an associated value of 24.
        OVERDUE: An alert type indicating an overdue alert with an associated value of 48.

    Methods:
        __str__: Returns the name of the alert type as a string.
    """
    WARNING = 5
    CRITICAL_WARNING = 24
    OVERDUE = 48

    def __str__(self):
        return self.name


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


class EmailMsgImportanceLevel(IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2

    def __str__(self):
        return self.name
