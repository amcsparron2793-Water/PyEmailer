from typing import Optional, Callable, TYPE_CHECKING

from PyEmailerAJM.backend import AlertTypes
from PyEmailerAJM.continuous_monitor.backend.continuous_monitor_base import ContinuousMonitorBase

if TYPE_CHECKING:
    from PyEmailerAJM.continuous_monitor import ContinuousMonitorAlertSend
from PyEmailerAJM.msg import MsgFactory


class ContinuousMonitor(ContinuousMonitorBase):
    TITLE_STRING = " Watching for emails with alerts in {} folder ".center(100, '*')
    MSG_FACTORY_CLASS: MsgFactory = MsgFactory

    def GetMessages(self, folder_index=None):
        """
        :param folder_index: Index of the folder from which messages are retrieved. Defaults to None if not specified.
        :type folder_index: int, optional
        :return: A list of sorted and filtered message objects, each containing an alert.
        :rtype: list
        """
        msgs = super().GetMessages(folder_index)
        sorted_msgs = [self.__class__.MSG_FACTORY_CLASS.get_msg(x, logger=self.logger, snooze_checker=self.snooze_tracker) for x in msgs]
        alert_messages = [x for x in sorted_msgs if x is not None and x.msg_alert]
        return alert_messages

    def _set_args_for_endless_watch(self):
        """
        Sets specific arguments for the endless_watch process.

        :return: None
        :rtype: None
        """
        self.send_emails = False
        self.auto_send = False
        self.display_window = False

    def _print_and_send(self, alert_level):
        """
        :param alert_level: The level of alert to be logged and potentially emailed.
        :type alert_level
        :return: None
        :rtype: None
        """
        if not self.dev_mode:
            self.logger.info(f"{alert_level} found!", print_msg=True)
        else:
            self.logger.info(f"{alert_level} found!", print_msg=True)
            self.logger.warning("IS DEV MODE - NOT postprocessing")

    def check_for_alerts(self):
        """
        Checks for emails in the specified folder and identifies if there are any alerts. Alerts,
        if present, are categorized as overdue, warning, or critical warning, and are processed accordingly.
        Then logs the result of the check.

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

    def endless_watch(self, stop_condition: Callable[[], bool] = None):
        if not self.dev_mode:
            self._set_args_for_endless_watch()

        stop_condition = stop_condition or (lambda: False)  # Default stop_condition
        email_dir_name = self.read_folder.name if self.read_folder else None

        self.logger.info(self.__class__.TITLE_STRING.format(email_dir_name), print_msg=True)

        while not stop_condition():
            try:
                self.check_for_alerts()
                self._was_refreshed = False
                self.sleep_timer.sleep_in_rounds()
            except KeyboardInterrupt:
                self.logger.error("KeyboardInterrupt detected, exiting program.")
                break


if __name__ == '__main__':
    ContinuousMonitor.MSG_FACTORY_CLASS.ALERT_SUBJECT_KEYWORDS = ['training']
    cm = ContinuousMonitor(False, False, dev_mode=False, show_warning_logs_in_console=True, )
    cm.endless_watch()
