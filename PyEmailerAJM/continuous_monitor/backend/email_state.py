from abc import abstractmethod, ABCMeta
from logging import Logger
from typing import Optional
from enum import Enum as _Enum
from PyEmailerAJM.backend import AlertTypes
from PyEmailerAJM.backend import NoMessagesFetched


class EmailState(metaclass=ABCMeta):
    """
    Represents the state and behavior associated with processing email messages
    and evaluating their alert levels (Overdue, Critical Warning, Warning).

    This class is enum-agnostic: subclasses can swap in a different Enum type
    that defines WARNING, CRITICAL_WARNING, and OVERDUE members via the
    class attribute `ALERT_ENUM` while keeping the same structure/checking.

    Attributes:
        logger: A logger object used to log messages and events during message processing.
        all_messages: A collection of all retrieved email messages.
        _was_refreshed: A boolean indicating whether the messages have been refreshed.
        ALERT_ENUM: Enum class used to represent alert levels. Defaults to backend.AlertTypes.

    Methods:
        __init__:
            Initializes the EmailState instance with default values.

        GetMessages:
            An abstract method to be implemented by subclasses for retrieving email messages.

        _raise_no_messages:
            Raises a NoMessagesFetched exception if email messages have not been populated.

        refresh_messages:
            Populates the `all_messages` attribute by fetching the latest messages
            using the `GetMessages` method and updates `_was_refreshed` to True.

    Properties:
        has_overdue:
            Indicates if there are any messages with an alert level of Overdue.
            Raises NoMessagesFetched if messages have not been refreshed.

        has_critical_warning:
            Indicates if there are any messages with a critical warning alert level.
            Raises NoMessagesFetched if messages have not been refreshed.

        has_warning:
            Indicates if there are any messages with a warning alert level present.
            Raises NoMessagesFetched if messages have not been refreshed.
    """

    # Enum to use for alert comparisons; can be overridden by subclasses
    ALERT_ENUM = AlertTypes
    ALERT_CRITICAL_MEMBERS: tuple[str, ...] = ("WARNING", "CRITICAL_WARNING", "OVERDUE")

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

    @property
    def has_overdue(self):
        """
        Checks if there are any overdue messages among all messages. A message is considered overdue if its alert level
        matches the AlertTypes.OVERDUE constant. If no messages have been fetched and the flag _was_refreshed is False,
        it raises an exception indicating no messages are available.

        :return: True if there are overdue messages, False otherwise.
        :rtype: bool
        """
        if self.all_messages:
            enum_cls = self.__class__.ALERT_ENUM
            return any([x for x in self.all_messages
                        if x.__class__.ALERT_LEVEL == enum_cls.OVERDUE])
        if not self._was_refreshed:
            self._raise_no_messages()

    # TODO: generalize these properties into a single method that takes an alert level enum and returns a boolean
    @property
    def has_critical_warning(self):
        """
        Checks if there are any messages with a critical warning alert level.

        :return: A boolean indicating whether there is at least one message with a critical warning alert level
        :rtype: bool

        """
        if self.all_messages:
            enum_cls = self.__class__.ALERT_ENUM
            return any([x for x in self.all_messages
                        if x.__class__.ALERT_LEVEL == enum_cls.CRITICAL_WARNING])
        elif not self._was_refreshed:
            self._raise_no_messages()

    @property
    def has_warning(self):
        """
        :return: Indicates whether there are any messages of warning level present.
        :rtype: bool
        """
        if self.all_messages:
            enum_cls = self.__class__.ALERT_ENUM
            return any([x for x in self.all_messages
                        if x.__class__.ALERT_LEVEL == enum_cls.WARNING])
        elif not self._was_refreshed:
            self._raise_no_messages()