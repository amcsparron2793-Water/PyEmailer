from datetime import datetime

import win32com.client as win32
# pylint: disable=import-error
from PyEmailerAJM.msg import Msg
from PyEmailerAJM.backend import TheSandman
from PyEmailerAJM.backend import AlertTypes


class _AlertMsgBase(Msg):
    """
    A base class for alert message handling that inherits from ``Msg``.
    This class is designed to evaluate whether a message meets specific
    alert conditions, such as being unread, not recent, and matching predefined subject keywords.

    Attributes:
        ALERT_LEVEL (AlertTypes, optional): The alert level for the message, should be of type ``AlertTypes``.
        ALERT_TIME_HOURS (int or None): Represents the time, in hours, for an alert validity period.
            Derived from ``ALERT_LEVEL.value`` if ``ALERT_LEVEL`` is set.
        _ALERT_TIME_HOURS_ERROR (str): Message displayed when ``ALERT_TIME_HOURS`` is not properly set.

    Methods:
        __init__(self, email_item, **kwargs):
            Initializes the alert message object. Determines the cap for recent days
                from the provided or default ``ALERT_TIME_HOURS``.

        __init_subclass__(cls, **kwargs):
            Ensures subclasses properly define the ``ALERT_LEVEL`` attribute as an ``AlertTypes`` value.

        msg_alert (bool):
            Checks if the message is alert-worthy, determining conditions such as
                being unread, not recent, and containing alert keywords.

        alert_time_days (float or None):
            Retrieves the allowed alert time in days, converted from hours.

        get_alert_time_days(cls) -> float or None:
            Returns the converted alert time from hours to days at the class level.
                If errors occur during conversion, it returns ``None``.

        _msg_is_recent(self, days_limit=None) -> bool:
            Determines whether a message is recent based on a specified or default days limit.

        msg_is_rfi(cls, msg) -> bool:
            Verifies if the message subject contains any predefined RFI keywords.
    """
    ALERT_LEVEL: AlertTypes = None
    ALERT_TIME_HOURS = ALERT_LEVEL.value if ALERT_LEVEL else None
    _ALERT_TIME_HOURS_ERROR = 'ALERT_TIME_HOURS must be set to an INT value when using this class!'
    ALERT_SUBJECT_KEYWORD_ERROR = ('ALERT_SUBJECT_KEYWORDS must be a non-empty list of strings! '
                                   'Override in factory class if needed.')
    ATTRS_TO_CHECK = ['ALERT_SUBJECT_KEYWORDS']

    # noinspection PyUnresolvedReferences
    def __init__(self, email_item: win32.CDispatch or 'extract_msg.Message', **kwargs):
        if isinstance(email_item, Msg):
            email_item = email_item()

        self.logger = kwargs.get('logger', None)

        super().__init__(email_item, **kwargs)

        self.recent_days_cap = kwargs.get('recent_days_cap', self.__class__.ALERT_TIME_HOURS)
        self._msg_snoozed = None
        self._msg_snoozed_time = None
        self.snooze_checker = kwargs.get('snooze_checker', None)
        self.__class__.AlertMsgBaseCheckClsAttrs()

    def __init_subclass__(cls, **kwargs):
        if cls.ALERT_LEVEL and isinstance(cls.ALERT_LEVEL, AlertTypes):
            pass
        else:
            raise AttributeError('ALERT_LEVEL must be set to an AlertTypes value when using this class!')

    @classmethod
    def AlertMsgBaseCheckClsAttrs(cls):
        # FIXME: this should go with each of the alert_msgs??
        if issubclass(cls, _AlertMsgBase):
            cls.check_for_class_attrs(cls.ATTRS_TO_CHECK)

    @classmethod
    def check_for_class_attrs(cls, class_attrs_to_check):
        for c in class_attrs_to_check:
            if hasattr(cls, c) and isinstance(getattr(cls, c), list) and len(getattr(cls, c)) > 0:
                continue
            raise AttributeError(cls.ALERT_SUBJECT_KEYWORD_ERROR)

    def _still_snoozed_check(self):
        snooze_checker_entry = self.snooze_checker.read_entry(self.subject)

        if not snooze_checker_entry and self.msg_snoozed_time:
            snooze_expired = TheSandman.is_snooze_expired(self.msg_snoozed_time)
        elif not snooze_checker_entry and not self.msg_snoozed_time:
            snooze_expired = True
        else:
            snooze_expired = TheSandman.is_snooze_expired(snooze_checker_entry)

        if not snooze_expired:
            self.msg_snoozed = True
            return True
        self.msg_snoozed = False
        return False
        # return False

    def _remove_unread_from_snoozed(self):
        self.logger.debug("msg is not unread, removing from snooze list if present")
        self.snooze_checker.json_loaded.pop(self.subject, None)
        self.snooze_checker.save_json()

    @property
    def msg_alert(self):
        """
        Check if the message is alert worthy, meaning it is unread and not recent.

        :return: True if the email item is unread and not recent, otherwise False.
        :rtype: bool
        """
        if not self.email_item.Unread:
            self._remove_unread_from_snoozed()
            return False

        still_snoozed = self._still_snoozed_check()
        if not still_snoozed:
            if self.email_item.Unread and not self._msg_is_recent() and self.msg_is_alert(self):
                return True
        return False

    @property
    def msg_snoozed(self):
        """
        :return: The snoozed message status.
        :rtype: bool
        """
        return self._msg_snoozed

    @msg_snoozed.setter
    def msg_snoozed(self, value: bool):
        """
        Setter method for the `msg_snoozed` property. Updates the snooze status and sets the snooze timestamp if the status is enabled.

        :param value: Indicates whether the message is snoozed. If True, sets the snooze timestamp to the current datetime, otherwise resets it to None.
        :type value: bool
        """
        self._msg_snoozed = value
        self._msg_snoozed_time = datetime.now() if value else None

    @property
    def msg_snoozed_time(self):
        """
        :return: The snoozed time of the message.
        :rtype: int or None
        """
        return self._msg_snoozed_time

    @property
    def alert_time_days(self):
        """
        :return: The alert time in days.
        :rtype: int
        """
        return self.get_alert_time_days()

    @classmethod
    def get_alert_time_days(cls):
        """
        Calculates the alert time in days based on the class attribute ALERT_TIME_HOURS.
        If ALERT_TIME_HOURS is not defined or is invalid (e.g., a type error or division by zero), returns None.

        :return: The alert time in days or None if an error occurs.
        :rtype: float or None
        """
        try:
            return cls.ALERT_TIME_HOURS / 24
        except (TypeError, ZeroDivisionError) as e:
            return None

    def _msg_is_recent(self, days_limit=None):
        """
        :param days_limit: The number of days to consider when determining if a message is recent.
            If not provided, defaults to the value of `self.recent_days_cap`.
        :type days_limit: int, optional
        :return: A boolean indicating whether the message is recent based on the given or default days limit.
        :rtype: bool
        """
        days_limit = days_limit if days_limit else self.alert_time_days
        return super()._msg_is_recent(recent_days_cap=days_limit)

    @classmethod
    def msg_is_alert(cls, msg: Msg):
        """
        Checks if the message subject contains any predefined alert keywords.

        :return: True if the subject contains any alert keywords, False otherwise
        :rtype: bool
        """
        if any((x for x in getattr(cls, 'ALERT_SUBJECT_KEYWORDS')
                if x.lower() in msg.subject.lower())):
            return True
        return False


class _WarningMsg(_AlertMsgBase):
    """
    A warning message class that inherits from the base alert message class.

    Attributes:
        ALERT_LEVEL: Represents the alert type, in this case, set to WARNING.
        ALERT_TIME_HOURS: Duration in hours associated with the warning level, derived from ALERT_LEVEL.
    """
    ALERT_LEVEL = AlertTypes.WARNING
    ALERT_TIME_HOURS = ALERT_LEVEL.value if ALERT_LEVEL else None


class _CriticalWarningMsg(_AlertMsgBase):
    """
    Represents a critical warning alert message.

    This class is a specialization of the `_AlertMsgBase` class tailored to handle
    critical warning alerts. It defines specific attributes such as `ALERT_LEVEL`
    and `ALERT_TIME_HOURS`, which determines the severity and time-related settings
    of the alert.

    Attributes
    ----------
    ALERT_LEVEL : AlertTypes
        A constant representing the severity level of this alert, set to
        `AlertTypes.CRITICAL_WARNING`.
    ALERT_TIME_HOURS : int or None
        The time duration associated with this alert in hours. Derived from the
        value of `ALERT_LEVEL` if available, otherwise `None`.
    """
    ALERT_LEVEL = AlertTypes.CRITICAL_WARNING
    ALERT_TIME_HOURS = ALERT_LEVEL.value if ALERT_LEVEL else None


class _OverDueMsg(_AlertMsgBase):
    """
    Represents a specialized message object that determines if a message is overdue
        or related to a Request For Information (RFI).

    Attributes:
        ALERT_SUBJECT_KEYWORDS: List of keywords used to identify if a message
            subject relates to a Request For Information (RFI).

    Methods:
        __init__(email_item, **kwargs):
            Initializes the _OverDueMsg object with an email item and optional parameters such as recent_days_cap.

        _msg_is_recent(days_limit=None):
            Determines whether the message is recent based on the number of days provided
                or the default recent_days_cap.

    Properties:
        msg_alert:
            Checks if the message is unread and not recent, marking it as overdue.

        msg_is_rfi:
            Checks if the message subject matches any of the predefined RFI keywords, marking it as related to an RFI.
    """
    ALERT_LEVEL = AlertTypes.OVERDUE
    ALERT_TIME_HOURS = ALERT_LEVEL.value if ALERT_LEVEL else None
