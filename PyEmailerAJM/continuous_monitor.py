from typing import Optional
from pathlib import Path

from PyEmailerAJM import PyEmailer
from PyEmailerAJM.backend import (EmailState, SnoozeTracking,
                                  TheSandman, AlertTypes,
                                  ContinuousColorizer, PyEmailerLogger)
from PyEmailerAJM.msg import MsgFactory

NO_COLORIZER = False


class ContinuousMonitor(PyEmailer, EmailState):
    ADMIN_EMAIL_LOGGER = ['amcsparron@albanyny.gov']
    ADMIN_EMAIL = ['amcsparron@albanyny.gov']
    DEFAULT_SUBJECT = "Email Alert"
    DEFAULT_MSG_BODY = (f"Dear {', '.join([x.split('@')[0] for x in ADMIN_EMAIL])},\n\n"
                        "There is an Email in the inbox that has an alert ({msg_tuple}). \n\n"
                        "Thanks,\n"
                        "{email_sender}")
    TITLE_STRING = " Watching for emails with alerts in {} folder ".center(100, '*')

    def __init__(self, display_window: bool, send_emails: bool, **kwargs):
        self._elog = PyEmailerLogger(**kwargs)
        self.logger = self._elog()
        super().__init__(display_window, send_emails, logger=self.logger, **kwargs)

        self.colorizer = ContinuousColorizer(logger=self.logger)
        self.dev_mode = kwargs.get('dev_mode', False)
        self.snooze_tracker = SnoozeTracking(Path(kwargs.get('file_name', './snooze_tracker.json')),
                                             logger=kwargs.get('logger', self.logger))

        if self.dev_mode:
            self.logger.warning("DEV MODE ACTIVATED!")
            self.logger.warning(
                f"WARNING: this is a DEVELOPMENT MODE emailer,"
                f" it will mock send emails but not actually send them to {self.__class__.ADMIN_EMAIL}"
            )
        if self.dev_mode:
            self.logger.warning("email handler disabled for dev mode")
        else:
            self._elog.setup_email_handler(email_msg=self.email,
                                           logger_admins=self.__class__.ADMIN_EMAIL_LOGGER)

        self.sleep_timer = TheSandman(sleep_time_seconds=kwargs.get('sleep_time_seconds', None), logger=self.logger)

    def GetMessages(self, folder_index=None):
        """
        :param folder_index: Index of the folder from which messages are retrieved. Defaults to None if not specified.
        :type folder_index: int, optional
        :return: A list of sorted and filtered message objects, each containing an alert.
        :rtype: list
        """
        msgs = super().GetMessages(folder_index)
        sorted_msgs = [MsgFactory.get_msg(x, logger=self.logger, snooze_checker=self.snooze_tracker) for x in msgs]
        alert_messages = [x for x in sorted_msgs if x is not None and x.msg_alert]
        return alert_messages

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
        Processes and formats the response body by compiling alert messages and their corresponding alert levels, then generating a formatted string containing a summary of these messages.

        :return: Processed and formatted response body string
        :rtype: str
        """
        alert_msgs = [(x.subject, self.get_response_body_alert_level(x)) for x in self.GetMessages()]
        msg_tuple = ', '.join([' - '.join(x) for x in alert_msgs])
        return self.__class__.DEFAULT_MSG_BODY.format(email_sender=self.email_signature,
                                                      msg_tuple=msg_tuple).replace('\n', '<br>')

    def _set_args_for_endless_watch(self):
        """
        Sets specific arguments for the endless_watch process.

        :return: None
        :rtype: None
        """
        self.send_emails = True
        self.auto_send = True
        self.display_window = False
        self.logger.debug("send_emails, auto_send, and display_window set to True for endless_watch()")

    def _print_and_send(self, alert_level):
        """
        :param alert_level: The level of alert to be logged and potentially emailed.
        :type alert_level
        :return: None
        :rtype: None
        """
        if not self.dev_mode:
            self.logger.info(f"{alert_level} found! sending email...", print_msg=True)
        else:
            self.logger.info(f"{alert_level} found!", print_msg=True)
            self.logger.warning("IS DEV MODE - NOT sending email...")

        self.SendOrDisplay()

    def check_for_alerts(self):
        """
        Checks for emails in the specified folder and identifies if there are any alerts. Alerts, if present, are categorized as overdue, warning, or critical warning, and are processed accordingly. Logs the result of the check.

        :return: None
        :rtype: None

        """
        self.logger.info("\nChecking for emails with an alert...", print_msg=True)
        self.refresh_messages()
        if self.has_overdue:
            self._print_and_send(AlertTypes.OVERDUE)

        elif self.has_warning:
            self._print_and_send(AlertTypes.WARNING)

        elif self.has_critical_warning:
            self._print_and_send(AlertTypes.CRITICAL_WARNING)

        else:
            self.logger.info(f"No emails with an alert detected in {self.read_folder}", print_msg=True)

        self.snooze_tracker.snooze_msgs(self.all_messages)

    def endless_watch(self):
        """
        Watches for RFI emails with alerts in the specified folder endlessly in a loop. If not in developer mode, prepares arguments for the endless watch. Logs activity information and checks for alerts continuously. The loop can be interrupted with a keyboard interrupt, which halts the process gracefully.

        :return: None
        :rtype: None

        """
        if not self.dev_mode:
            self._set_args_for_endless_watch()
        email_dir_name = None
        if self.read_folder:
            email_dir_name = self.read_folder.name
        self.logger.info(self.__class__.TITLE_STRING.format(email_dir_name),
                         print_msg=True)

        while True:
            try:
                self.check_for_alerts()
                self._was_refreshed = False
                self.sleep_timer.sleep_in_rounds()
            except KeyboardInterrupt:
                print("goodbye")
                self.logger.error("KeyboardInterrupt detected, exiting program.")
                break


if __name__ == '__main__':
    cm = ContinuousMonitor(False, False, dev_mode=True, show_warning_logs_in_console=True,)
    cm.endless_watch()
