from ..backend.errs import InvalidAlertLevel
from .alert_messages import _AlertMsgBase, _OverDueMsg, _CriticalWarningMsg, _WarningMsg
from ..backend.enums import AlertTypes


# pylint: disable=too-few-public-methods
class MsgFactory:
    """
    Class MsgFactory:
    A factory class for creating and determining the appropriate alert message object
    based on the given message and its alert level.

    Class Attributes:
        MSG_CLASSES: A list of message type classes, representing potential alert message
        types in the order of evaluation for determining the alert level.

    Methods:
        _check_alert_level(msg, **kwargs):
            Iterates through the defined message type classes (MSG_CLASSES) and
            determines the alert type for the given message. Returns the first
            message object with a valid alert type.

        get_msg(msg, **kwargs):
            Determines and constructs the appropriate alert message object based on the
            `ALERT_LEVEL` of the given message. If `ALERT_LEVEL` is not defined,
            attempts to infer and determine the alert type using `_check_alert_level`.
            Raises InvalidAlertLevel if the alert level does not match any valid value.
    """
    # order is VERY IMPORTANT
    MSG_CLASSES = [_OverDueMsg, _CriticalWarningMsg, _WarningMsg]

    @classmethod
    def _check_alert_level(cls, msg, **kwargs):
        """
        :param msg: The message object to be evaluated against the alert level.
        :type msg: object
        :param kwargs: Additional arguments that might be required to determine the message type.
        :type kwargs: dict
        :return: The message type instance if an alert level is detected, otherwise None.
        :rtype: object or None
        """
        for msg_type_class in cls.MSG_CLASSES:
            m_type = msg_type_class(msg, **kwargs)
            if m_type.msg_alert:
                return m_type

    @classmethod
    def get_msg(cls, msg: _AlertMsgBase, **kwargs):
        """
        :param msg: An instance of the message class to be processed.
        :type msg: _AlertMsgBase
        :param kwargs: Additional arguments to be passed for message processing.
        :type kwargs: dict
        :return: An instance of the appropriate alert message class based on
            the ALERT_LEVEL of the provided message.
        :rtype: Union[_WarningMsg, _CriticalWarningMsg, _OverDueMsg]
        :raises InvalidAlertLevel: If the ALERT_LEVEL of the provided message is not recognized.
        """
        if hasattr(msg.__class__, 'ALERT_LEVEL'):
            if not isinstance(msg.ALERT_LEVEL, AlertTypes):
                raise InvalidAlertLevel(msg)
            if msg.ALERT_LEVEL.value == AlertTypes.WARNING.value:
                return _WarningMsg(msg(), **kwargs)
            if msg.ALERT_LEVEL.value == AlertTypes.CRITICAL_WARNING.value:
                return _CriticalWarningMsg(msg(), **kwargs)
            if msg.ALERT_LEVEL.value == AlertTypes.OVERDUE.value:
                return _OverDueMsg(msg(), **kwargs)
            else:
                raise InvalidAlertLevel(msg)
        # if it doesn't have an alert_level, then guess and check.
        return cls._check_alert_level(msg, **kwargs)
