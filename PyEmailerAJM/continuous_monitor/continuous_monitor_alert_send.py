from typing import Optional

from PyEmailerAJM.continuous_monitor import ContinuousMonitor

NO_COLORIZER = False


class ContinuousMonitorAlertSend(ContinuousMonitor):
    ADMIN_EMAIL_LOGGER = []
    ADMIN_EMAIL = []
    DEFAULT_SUBJECT = "Email Alert"
    DEFAULT_MSG_BODY = (f"Dear {', '.join([x.split('@')[0] for x in ADMIN_EMAIL])},\n\n"
                        "There is an Email in the inbox that has an alert ({msg_tuple}). \n\n"
                        "Thanks,\n"
                        "{email_sender}")
    ATTRS_TO_CHECK = ['ADMIN_EMAIL', 'ADMIN_EMAIL_LOGGER']

    def __init__(self, display_window: bool, send_emails: bool, **kwargs):

        super().__init__(display_window, send_emails, **kwargs)
        if not self.dev_mode:
            if type(self) is ContinuousMonitorAlertSend:
                self.__class__.check_for_class_attrs(self.__class__.ATTRS_TO_CHECK)
        else:
            self.logger.warning(f"IS DEV MODE - NOT checking for class attributes "
                                f"({', '.join(self.__class__.ATTRS_TO_CHECK)}) for ContinuousMonitorAlertSend")

    def __init_subclass__(cls, **kwargs):
        cls.check_for_class_attrs(cls.ATTRS_TO_CHECK)



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
            recipient = self.__class__.ADMIN_EMAIL
            if isinstance(recipient, list):
                recipient = ' ;'.join(recipient)
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
    def response_body(self):
        """
        Processes and formats the response body by compiling alert messages and their corresponding alert levels,
            then generating a formatted string containing a summary of these messages.

        :return: Processed and formatted response body string
        :rtype: str
        """
        alert_msgs = [(x.subject, self.get_response_body_alert_level(x)) for x in self.GetMessages()]
        msg_tuple = ', '.join([' - '.join(x) for x in alert_msgs])
        return self.__class__.DEFAULT_MSG_BODY.format(email_sender=self.email_signature,
                                                      msg_tuple=msg_tuple).replace('\n', '<br>')

    def _print_and_send(self, alert_level):
        super()._print_and_send(alert_level)
        self.SendOrDisplay()