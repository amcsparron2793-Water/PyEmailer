from abc import abstractmethod
from logging import Logger
from typing import Optional
from . import AlertTypes
from . import NoMessagesFetched


class EmailState:
    """
    Represents the state and behavior associated with processing email messages
    and evaluating their alert levels (Overdue, Critical Warning, Warning).

    Attributes:
        logger: A logger object used to log messages and events during message processing.
        all_messages: A collection of all retrieved email messages.
        _was_refreshed: A boolean indicating whether the messages have been refreshed.

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
            Indicates if there are any messages with an alert level of Critical Warning.
            Raises NoMessagesFetched if messages have not been refreshed.

        has_warning:
            Indicates if there are any messages with an alert level of Warning.
            Raises NoMessagesFetched if messages have not been refreshed.
    """

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
        self.SetupEmail()
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
            return any([x for x in self.all_messages
                        if x.__class__.ALERT_LEVEL == AlertTypes.OVERDUE])
        if not self._was_refreshed:
            self._raise_no_messages()

    @property
    def has_critical_warning(self):
        """
        Checks if there are any messages with a critical warning alert level.

        :return: A boolean indicating whether there is at least one message with a critical warning alert level
        :rtype: bool

        """
        if self.all_messages:
            return any([x for x in self.all_messages
                        if x.__class__.ALERT_LEVEL == AlertTypes.CRITICAL_WARNING])
        elif not self._was_refreshed:
            self._raise_no_messages()

    @property
    def has_warning(self):
        """
        :return: Indicates whether there are any messages of warning level present.
        :rtype: bool
        """
        if self.all_messages:
            return any([x for x in self.all_messages
                        if x.__class__.ALERT_LEVEL == AlertTypes.WARNING])
        elif not self._was_refreshed:
            self._raise_no_messages()