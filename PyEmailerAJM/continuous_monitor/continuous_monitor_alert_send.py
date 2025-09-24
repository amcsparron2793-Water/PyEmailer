from typing import Optional

from PyEmailerAJM.continuous_monitor import ContinuousMonitor

NO_COLORIZER = False


class ContinuousMonitorAlertSend(ContinuousMonitor):
    ADMIN_EMAIL_LOGGER = []
    ADMIN_EMAIL = []
    DEFAULT_SUBJECT = "Email Alert"
    DEFAULT_MSG_BODY = ("Dear {admin_email_names},\n\n"
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

    def _set_args_for_endless_watch(self):
        self.send_emails = True
        self.auto_send = True
        self.display_window = False
        self.logger.debug("send_emails, auto_send, and display_window set to True for endless_watch()")

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
    def email_signature(self):
        return ('<br>'.join(super().email_signature.split('\n'))
                if super().email_signature is not None else None)

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
        formatted_admin_email_names = ', '.join([x.split('@')[0] for
                                                 x in self.__class__.ADMIN_EMAIL]
                                                ).replace('\n', '<br>')
        formatted_full_body = self.__class__.DEFAULT_MSG_BODY.format(email_sender=self.email_signature,
                                                                     msg_tuple=msg_tuple,
                                                                     admin_email_names=formatted_admin_email_names
                                                                     ).replace('\n', '<br>')
        return formatted_full_body

    def _postprocess_alert(self, alert_level=None, **kwargs):
        self.SendOrDisplay(**kwargs)

    def refresh_messages(self):
        self.SetupEmail()
        super().refresh_messages()


class MyContMonAlertSend(ContinuousMonitorAlertSend):
    ADMIN_EMAIL_LOGGER = ['amcsparron@albanyny.gov']
    ADMIN_EMAIL = ADMIN_EMAIL_LOGGER


if __name__ == '__main__':
    MyContMonAlertSend.MSG_FACTORY_CLASS.ALERT_SUBJECT_KEYWORDS = ['training']
    # ContinuousMonitorAlertSend.ADMIN_EMAIL = ['amcsparron@albanyny.gov']
    # ContinuousMonitorAlertSend.ADMIN_EMAIL_LOGGER = ContinuousMonitorAlertSend.ADMIN_EMAIL
    cm = MyContMonAlertSend(False, False,
                            dev_mode=False,
                            show_warning_logs_in_console=True)#, email_sig_filename='Andrew Full.txt')
    cm.endless_watch()
