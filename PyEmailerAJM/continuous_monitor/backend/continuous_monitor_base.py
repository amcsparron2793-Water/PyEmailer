from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PyEmailerAJM import PyEmailer, is_instance_of_dynamic
from PyEmailerAJM.backend import EmailState, SnoozeTracking, TheSandman
from . import ContinuousColorizer

if TYPE_CHECKING:
    from PyEmailerAJM.backend import AlertTypes


class ContinuousMonitorBase(PyEmailer, EmailState):
    """
    Class ContinuousMonitorBase provides functionality to initialize and manage continuous monitoring
    with optional email notifications. It extends the PyEmailer and EmailState classes and incorporates helper
    classes for additional functionalities.

    Attributes:
        ADMIN_EMAIL_LOGGER (list): A list to store administrator email loggers.
        ADMIN_EMAIL (list): A list to store administrator email addresses.
        ATTRS_TO_CHECK (list): A list of class attributes to validate during subclass initialization.

    Methods:
        __init__(display_window: bool, send_emails: bool, **kwargs):
            Initializes an instance of ContinuousMonitorBase, setting up logging, helper classes,
            and initial email configurations. This also checks for a development mode and applies any specified
            behavior accordingly.

        __init_subclass__(cls, **kwargs):
            Validates certain class attributes for subclasses by ensuring their presence
            and that they are non-empty lists.

        check_for_class_attrs(cls, class_attrs_to_check):
            Validates a list of class attributes to ensure they are defined, are lists,
            and contain email addresses.

        initialize_helper_classes(self, **kwargs):
            Sets up and returns instances of helper classes including ContinuousColorizer, SnoozeTracking,
            and TheSandman, each initialized with parameters from **kwargs.

        log_dev_mode_warnings(self):
            Logs warnings if the `dev_mode` attribute is set to True.

        email_handler_init(self):
            Configures the email handler unless running in development mode. Provides appropriate logging
            based on the current mode.
    """
    ADMIN_EMAIL_LOGGER = []
    ADMIN_EMAIL = []
    ATTRS_TO_CHECK = []

    def __init__(self, display_window: bool, send_emails: bool, **kwargs):
        super().__init__(display_window, send_emails, **kwargs)

        self.dev_mode = kwargs.get('dev_mode', False)
        self.colorizer, self.snooze_tracker, self.sleep_timer = self.initialize_helper_classes(**kwargs)

        self.log_dev_mode_warnings()
        self.email_handler_init()

    @classmethod
    def check_for_class_attrs(cls, class_attrs_to_check):
        for c in class_attrs_to_check:
            if hasattr(cls, c) and isinstance(getattr(cls, c), list) and len(getattr(cls, c)) > 0:
                continue
            raise ValueError(f"{c} must be a list of email addresses")

    def initialize_helper_classes(self, **kwargs):
        colorizer = ContinuousColorizer(logger=self.logger)
        snooze_tracker = SnoozeTracking(Path(kwargs.get('file_name', './snooze_tracker.json')),
                                        logger=kwargs.get('logger', self.logger))
        sleep_timer = TheSandman(sleep_time_seconds=kwargs.get('sleep_time_seconds', None), logger=self.logger)
        return colorizer, snooze_tracker, sleep_timer

    def log_dev_mode_warnings(self):
        if self.dev_mode:
            self.logger.warning("DEV MODE ACTIVATED!")
            self.logger.warning(
                f"WARNING: this is a DEVELOPMENT MODE emailer,"
                f" it will mock send emails but not actually send them to {self.__class__.ADMIN_EMAIL}"
            )

    def email_handler_init(self):
        if self.dev_mode:
            self.logger.warning("email handler disabled for dev mode")
        elif (not type(self).__name__ == "ContinuousMonitorAlertSend"
              and not is_instance_of_dynamic(self, "__main__.ContinuousMonitorAlertSend")):
            self.logger.warning(
                f"email handler not initialized because this is not a ContinuousMonitorAlertSend subclass"
            )
        else:
            self._elog.setup_email_handler(email_msg=self.email,
                                           logger_admins=self.__class__.ADMIN_EMAIL_LOGGER)
            self.logger.info("email handler initialized")

    def _print_and_postprocess(self, alert_level):
        """
        :param alert_level: The level of alert to be logged and potentially emailed.
        :type alert_level
        :return: None
        :rtype: None
        """
        if not self.dev_mode:
            self.logger.info(f"{alert_level} found!", print_msg=True)
            self._postprocess_alert(alert_level)
        else:
            self.logger.info(f"{alert_level} found!", print_msg=True)
            self.logger.warning("IS DEV MODE - NOT postprocessing")

    @abstractmethod
    def _postprocess_alert(self, alert_level: Optional['AlertTypes'] = None, **kwargs):
        ...
