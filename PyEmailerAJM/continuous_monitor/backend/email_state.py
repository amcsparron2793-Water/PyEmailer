from abc import abstractmethod, ABCMeta
from logging import Logger
from typing import Optional
from enum import Enum as _Enum
from PyEmailerAJM.backend import AlertTypes
from PyEmailerAJM.backend import NoMessagesFetched


class BaseEmailState(metaclass=ABCMeta):
    """
    Provides a base class for defining and managing the state of an email system.

    This class is intended to be subclassed to define specific email state behaviors.
    Subclasses should provide implementations for abstract methods and define the
    required class-level variables to ensure proper functionality.

    :ivar ALERT_ENUM: Enum to use for alert comparisons. Subclasses must define this.
    :type ALERT_ENUM: Enum
    :ivar ALERT_CRITICAL_MEMBERS: Tuple of enum member names that are critical and must exist
        in the ALERT_ENUM. This must be defined by subclasses.
    :type ALERT_CRITICAL_MEMBERS: tuple of str
    """
    # Enum to use for alert comparisons; can be overridden by subclasses
    ALERT_ENUM = None
    ALERT_CRITICAL_MEMBERS = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        enum_cls = cls._validate_alert_enum()
        cls._check_for_missing(enum_cls)

    @classmethod
    def _check_for_missing(cls, enum_cls):
        critical_members: tuple[str, ...] = getattr(cls, 'ALERT_CRITICAL_MEMBERS', ())
        missing = [m for m in critical_members if not hasattr(enum_cls, m)]
        if missing:
            raise AttributeError(
                f"ALERT_ENUM must define members: {', '.join(critical_members)} Missing: {', '.join(missing)}"
            )

    @classmethod
    def _validate_alert_enum(cls):
        # Validate ALERT_ENUM is an Enum subclass and has required members
        enum_cls = getattr(cls, 'ALERT_ENUM', None)
        if enum_cls is None:
            raise AttributeError("Subclasses of EmailState must define ALERT_ENUM.")
        if not isinstance(enum_cls, type) or not issubclass(enum_cls, _Enum):
            raise TypeError("ALERT_ENUM must be an Enum subclass.")
        return enum_cls

    def __init__(self):
        self.logger: Optional[Logger] = None
        self.all_messages = None
        self._was_refreshed = False

    @abstractmethod
    def GetMessages(self):
        """
        Retrieve messages from the implemented source.

        :return: Messages retrieved from the source
        :rtype: list
        """
        ...

    @abstractmethod
    def SetupEmail(self):
        ...

    def _raise_no_messages(self):
        """
        Raises a NoMessagesFetched exception, indicating that the `all_messages` attribute has not been populated.
        This suggests that the method `refresh_messages` should be executed to fetch and populate messages.

        :raises NoMessagesFetched: Exception raised when no messages have been fetched.
        """
        raise NoMessagesFetched("all_messages has not been populated, run self.refresh_messages() first.")

    def refresh_messages(self):
        """
        Refreshes the messages by retrieving them from the email folder.

        :return: None
        :rtype: None
        """
        self.logger.info("Refreshing messages from email folder...")
        self.all_messages = self.GetMessages()
        self._was_refreshed = True
        self.logger.info("Successfully refreshed messages from email folder.")

    def _has_alert_level(self, alert_level: _Enum) -> Optional[bool]:
        """
        Generic method to check if any messages in all_messages match the specified alert level.

        :param alert_level: The enum member to check for.
        :return: True if at least one message matches, False if none match, None if not refreshed.
        """
        if self.all_messages:
            return any(x.__class__.ALERT_LEVEL == alert_level for x in self.all_messages)
        if not self._was_refreshed:
            self._raise_no_messages()
        return False


class EmailState(BaseEmailState, metaclass=ABCMeta):
    """
    Represents an abstract base class for managing the state of email alerts and their associated levels.

    The class provides properties to evaluate the presence of specific alert levels (e.g., overdue, critical warnings,
    warnings) across the managed messages. Subclasses can customize the alert handling by overriding the
    ALERT_ENUM attribute. This class is intended to be extended for more specific implementations of email
    state management.

    :ivar ALERT_ENUM: Enum to use for alert comparisons; can be overridden by subclasses.
    :type ALERT_ENUM: type
    :ivar ALERT_CRITICAL_MEMBERS: A tuple consisting of alert levels considered critical.
    :type ALERT_CRITICAL_MEMBERS: tuple[str, ...]
    """

    # Enum to use for alert comparisons; can be overridden by subclasses
    ALERT_ENUM: AlertTypes = AlertTypes
    ALERT_CRITICAL_MEMBERS: tuple[str, ...] = ("WARNING", "CRITICAL_WARNING", "OVERDUE")

    @property
    def has_overdue(self):
        """
        Checks if there are any overdue messages among all messages. A message is considered overdue if its alert level
        matches the AlertTypes.OVERDUE constant. If no messages have been fetched and the flag _was_refreshed is False,
        it raises an exception indicating no messages are available.

        :return: True if there are overdue messages, False otherwise.
        :rtype: bool
        """
        return self._has_alert_level(self.__class__.ALERT_ENUM.OVERDUE)

    @property
    def has_critical_warning(self):
        """
        Checks if there are any messages with a critical warning alert level.

        :return: A boolean indicating whether there is at least one message with a critical warning alert level
        :rtype: bool

        """
        return self._has_alert_level(self.__class__.ALERT_ENUM.CRITICAL_WARNING)

    @property
    def has_warning(self):
        """
        :return: Indicates whether there are any messages of warning level present.
        :rtype: bool
        """
        return self._has_alert_level(self.__class__.ALERT_ENUM.WARNING)
