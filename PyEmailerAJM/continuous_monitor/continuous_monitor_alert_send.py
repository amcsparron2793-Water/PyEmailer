from abc import abstractmethod
from typing import Optional, TYPE_CHECKING, Union

from PyEmailerAJM.continuous_monitor import ContinuousMonitor
from PyEmailerAJM.backend import EmailMsgImportanceLevel

# This is installed as part of pywin32
# noinspection PyUnresolvedReferences
from pythoncom import com_error

if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from PyEmailerAJM.msg.alert_messages import _AlertMsgBase

NO_COLORIZER = False


class ContinuousMonitorAlertSend(ContinuousMonitor):
    """
    Handles sending email alerts for continuous monitoring functionality.

    This class extends the ContinuousMonitor class to include email alert configuration,
    response body formatting, and email importance settings. It facilitates monitoring
    operations with automated email notifications and provides tools for organizing and
    formatting alert information.

    :ivar ADMIN_EMAIL_LOGGER: Placeholder for logger-related administrative email information.
    :type ADMIN_EMAIL_LOGGER: list
    :ivar ADMIN_EMAIL: List of administrative email addresses for notification purposes.
    :type ADMIN_EMAIL: list
    :ivar DEFAULT_SUBJECT: Default subject line for email alerts.
    :type DEFAULT_SUBJECT: str
    :ivar DEFAULT_MSG_BODY: Template of the default email body content for alerts.
    :type DEFAULT_MSG_BODY: str
    :ivar ATTRS_TO_CHECK: List of attributes required to be present in the class.
    :type ATTRS_TO_CHECK: list
    :ivar ALERT_EMAIL_IMPORTANCE: Email importance level for alert emails.
    :type ALERT_EMAIL_IMPORTANCE: EmailMsgImportanceLevel
    :ivar DEFAULT_EMAIL_IMPORTANCE: Default importance level for general emails.
    :type DEFAULT_EMAIL_IMPORTANCE: EmailMsgImportanceLevel
    """
    ADMIN_EMAIL_LOGGER = []
    ADMIN_EMAIL = []
    DEFAULT_SUBJECT = "Email Alert"
    DEFAULT_MSG_BODY = ("Dear {admin_email_names},\n\n"
                        "There is an Email in the inbox that has an alert ({msg_tuple}). \n\n"
                        "Thanks,\n"
                        "{email_sender}")
    ATTRS_TO_CHECK = ['ADMIN_EMAIL', 'ADMIN_EMAIL_LOGGER']
    ALERT_EMAIL_IMPORTANCE = EmailMsgImportanceLevel.HIGH
    DEFAULT_EMAIL_IMPORTANCE = EmailMsgImportanceLevel.NORMAL

    def __init__(self, display_window: bool, send_emails: bool, **kwargs):

        super().__init__(display_window, send_emails, **kwargs)
        if not self.dev_mode:
            if type(self) is ContinuousMonitorAlertSend:
                self.__class__.check_for_class_attrs(self.__class__.ATTRS_TO_CHECK)
        else:
            self.logger.warning(f"IS DEV MODE - NOT checking for class attributes "
                                f"({', '.join(self.__class__.ATTRS_TO_CHECK)}) for ContinuousMonitorAlertSend")

    def _set_args_for_endless_watch(self):
        self.send_emails = True
        self.auto_send = True
        self.display_window = False
        self.logger.debug(f"Configured endless_watch: send_emails={self.send_emails}, "
                          f"auto_send={self.auto_send}, display_window={self.display_window}")

    def SetupEmail(self, recipient: Optional[str] = None, subject: str = DEFAULT_SUBJECT,
                   text: str = None, attachments: list = None, **kwargs):
        """
        :param recipient: Email recipient(s). If not provided, defaults to ADMIN_EMAIL or a semicolon-separated string of recipients in case of a list.
        :type recipient: Optional[str]
        :param subject: Subject of the email. Defaults to DEFAULT_SUBJECT.
        :type subject: str
        :param text: Body text of the email. If not provided, defaults to the response_body attribute.
        :type text: str
        :param attachments: A list of attachments to include in the email.
        :type attachments: list
        :param kwargs: Additional keyword arguments passed to the parent SetupEmail method.
        :type kwargs: dict
        :return: The resulting email setup performed by the superclass's SetupEmail method.
        :rtype: Any
        """
        if not recipient:
            recipient: Union[str, list] = self.__class__.ADMIN_EMAIL
            if isinstance(recipient, list):
                recipient: str = ' ;'.join(recipient)
        if not text:
            text = self.response_body
        return super().SetupEmail(recipient=recipient, subject=subject,
                                  text=text, attachments=attachments, **kwargs)

    def get_response_body_alert_level(self, msg: '_AlertMsgBase'):
        """
        :param msg: The message object which contains the alert level information.
        :type msg: _AlertMsgBase
        :return: The alert level string, optionally colorized if coloring is enabled.
        :rtype: str
        """
        if NO_COLORIZER:
            self.logger.debug("colorizer not available, using plain text for alert level")
            rb_alert_string = msg.__class__.ALERT_LEVEL.name
        else:
            self.logger.debug("colorizer available, using colorized alert level")
            color = self.colorizer.get_alert_color(msg.__class__.ALERT_LEVEL)
            rb_alert_string = self.colorizer.colorize(msg.__class__.ALERT_LEVEL.name,
                                                      color=color,
                                                      html_mode=True)
        return rb_alert_string

    @property
    def email_signature(self):
        return ('<br>'.join(super().email_signature.split('\n'))
                if super().email_signature is not None else None)

    @property
    def greeting_fmt_admin_email_names(self):
        formatted_admin_email_names = ', '.join([x.split('@')[0] for
                                                 x in self.__class__.ADMIN_EMAIL]
                                                )
        return self._py_to_html_breaks(formatted_admin_email_names)

    @property
    def response_body(self):
        """
        Processes and formats the response body by compiling alert messages and their corresponding alert levels,
            then generating a formatted string containing a summary of these messages.

        :return: Processed and formatted response body string
        :rtype: str
        """
        alert_msgs = [(x.subject, self.get_response_body_alert_level(x)) for x in self.GetMessages()]
        msg_tuple = ', '.join([' - '.join(x) for x in alert_msgs])
        fmt_keys = {"email_sender": self.email_signature,
                    "msg_tuple": msg_tuple,
                    "admin_email_names": self.greeting_fmt_admin_email_names}

        formatted_full_body = self.__class__.DEFAULT_MSG_BODY.format(**fmt_keys)
        return self._py_to_html_breaks(formatted_full_body)

    def _set_email_importance(self, importance_level=None, **kwargs):
        default_importance = kwargs.get('default_importance', self.__class__.DEFAULT_EMAIL_IMPORTANCE)
        try:
            if importance_level is None:
                self.email.importance = self.__class__.ALERT_EMAIL_IMPORTANCE
            else:
                self.email.importance = importance_level
        except (com_error, TypeError) as e:
            self.logger.warning(f"Invalid Importance level ({importance_level}) for email,"
                                f" setting to {default_importance}")
            self.email.importance = default_importance
            return self.email
        return self.email

    def _postprocess_alert(self, alert_level=None, **kwargs):
        self._set_email_importance(**kwargs)
        self.SendOrDisplay(**kwargs)

    def refresh_messages(self):
        self.email = self.initialize_new_email()
        self.SetupEmail()
        super().refresh_messages()


class NonEmailTriggerCMAS(ContinuousMonitorAlertSend):
    """
    Represents a specialized alert monitoring class for situations that do not involve email-based alerts.

    This class defines mechanisms to monitor and process non-email-based alerts, creating customized
    alert messages and behavior tailored to specific scenarios. It provides a framework for handling alert
    situations through abstract methods and overrides specific alert-related logic.

    :ivar DEFAULT_MSG_BODY: Default template for the alert message body.
    :type DEFAULT_MSG_BODY: str
    :ivar TITLE_STRING: Title string used for display purposes, formatted with asterisks.
    :type TITLE_STRING: str
    :ivar ALERT_CHECK_STR: String indicating that an alert check is in progress.
    :type ALERT_CHECK_STR: str
    :ivar NO_ALERTS_STR: String displayed when no alerts are detected.
    :type NO_ALERTS_STR: str
    """
    DEFAULT_MSG_BODY = ("Dear {admin_email_names},\n\n"
                        "There is SOMETHING that requires attention. \n\n"
                        "Thanks,\n"
                        "{email_sender}")
    TITLE_STRING = " Watching for an alert ".center(100, '*')
    ALERT_CHECK_STR = "Checking for an alert..."
    NO_ALERTS_STR = "No alerts detected."

    @property
    def response_body(self):
        sub_text = self.__class__.DEFAULT_MSG_BODY.format(email_sender=self.email_signature,
                                                          admin_email_names=self.greeting_fmt_admin_email_names
                                                          )
        return self._py_to_html_breaks(sub_text)

    def GetMessages(self, folder_index=None):
        self.logger.debug(f"{self.__class__.__name__}.GetMessages() disabled - returning empty list")
        return []

    def _setup_snooze_tracker_helper(self, **kwargs):
        self.logger.debug(f"{self.__class__.__name__}.snooze_tracker disabled - returning None")
        return None

    @abstractmethod
    def _classify_and_process(self, **kwargs):
        # TODO: implement this without relying on EmailState
        # EX :         if not self.is_machine_up:
        #                   self._process_machine_down(**kwargs)
        #                   return
        #
        #         if not self.is_server_up:
        #             self._process_server_down(**kwargs)
        #         else:
        #             self._process_no_alert(**kwargs)
        ...


class _NETCMALTest(NonEmailTriggerCMAS):
    def _classify_and_process(self, **kwargs):
        alert_found = kwargs.get('alert_found', True)
        print("_NETCMALTest.classify_and_process() called")
        if alert_found:
            self._print_and_postprocess(None)
        else:
            self._process_no_alert(**kwargs)


if __name__ == '__main__':
    ContinuousMonitorAlertSend.MSG_FACTORY_CLASS.ALERT_SUBJECT_KEYWORDS = ['training']
    _NETCMALTest.ADMIN_EMAIL = ['amcsparron@albanyny.gov']
    _NETCMALTest.ADMIN_EMAIL_LOGGER = _NETCMALTest.ADMIN_EMAIL
    cm = _NETCMALTest(False, False,
                      dev_mode=True,
                      show_warning_logs_in_console=True)  #, email_sig_filename='Andrew Full.txt')
    cm.endless_watch()
