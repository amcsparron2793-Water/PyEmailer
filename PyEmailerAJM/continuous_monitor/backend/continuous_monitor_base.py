from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PyEmailerAJM import PyEmailer, is_instance_of_dynamic
from PyEmailerAJM.backend import TheSandman
from . import ContinuousColorizer, SnoozeTracking, EmailState

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
        # Let EmailerInitializer handle logger factory vs instance normalization
        super().__init__(display_window, send_emails, **kwargs)

        self.dev_mode = kwargs.get('dev_mode', False)
        self.colorizer, self.snooze_tracker, self.sleep_timer = self.initialize_helper_classes(**kwargs)

        self.log_dev_mode_warnings()
        self.email_handler_init()

    @property
    def num_snoozed_msgs(self):
        if (self.snooze_tracker.json_loaded and
                hasattr(self.snooze_tracker.json_loaded, '__len__')):
            return len(self.snooze_tracker.json_loaded)
        else:
            return 0

    @classmethod
    def check_for_class_attrs(cls, class_attrs_to_check):
        for c in class_attrs_to_check:
            if hasattr(cls, c) and isinstance(getattr(cls, c), list) and len(getattr(cls, c)) > 0:
                continue
            raise ValueError(f"{c} must be a list of email addresses")

    def _normalize_logger(self, **kwargs):
        # Normalize logger: if it's a factory, call it to get the instance
        logger_arg = kwargs.pop('logger', self.logger)
        if callable(logger_arg) and not hasattr(logger_arg, 'info'):
            # It's a factory, not a logger instance
            logger = logger_arg()
        else:
            logger = logger_arg
        return logger

    def initialize_helper_classes(self, **kwargs):
        """
        Initializes and returns instances of helper classes based on provided parameters.

        This method is responsible for creating and configuring instances of helper
        classes. It extracts configuration from the provided keyword arguments, uses
        default class constructors when not overridden, and ensures logging and other
        options are properly normalized and propagated.

        :param kwargs: Configuration and initialization parameters for helper classes.
        :type kwargs: dict
        :return: A tuple containing instances of colorizer, snooze_tracker, and
                 sleep_timer in that order.
        :rtype: tuple
        """
        logger = self._normalize_logger(**kwargs)
        # Remove old logger from kwargs after normalization
        kwargs.pop('logger', None)

        # Extract helper class factories with defaults
        colorizer_class = kwargs.pop('colorizer', ContinuousColorizer)
        snooze_tracker_class = kwargs.pop('snooze_tracker', SnoozeTracking)
        sleep_timer_class = kwargs.pop('sleep_timer', TheSandman)

        # Initialize helper instances
        colorizer = colorizer_class(logger=logger, **kwargs)

        snooze_file_path = Path(kwargs.pop('file_name', './snooze_tracker.json'))
        snooze_tracker = snooze_tracker_class(file_path=snooze_file_path, logger=logger, **kwargs)

        sleep_time_seconds = kwargs.pop('sleep_time_seconds', None)
        sleep_timer = sleep_timer_class(sleep_time_seconds=sleep_time_seconds,
                                        logger=logger, **kwargs)

        return colorizer, snooze_tracker, sleep_timer

    def log_dev_mode_warnings(self):
        if self.dev_mode:
            self.logger.warning("DEV MODE ACTIVATED!")
            self.logger.warning(
                f"WARNING: this is a DEVELOPMENT MODE emailer,"
                f" it will mock send emails but not actually send them to {self.__class__.ADMIN_EMAIL}"
            )

    def _is_continuous_monitor_alert_send_subclass(self):
        """Check if this instance is a ContinuousMonitorAlertSend subclass."""
        is_named_match = type(self).__name__ == "ContinuousMonitorAlertSend"
        is_dynamic_match = is_instance_of_dynamic(self, "__main__.ContinuousMonitorAlertSend")
        return is_named_match or is_dynamic_match

    def _should_skip_email_handler_init(self):
        """Determine if email handler initialization should be skipped."""
        if self.dev_mode:
            self.logger.warning("email handler disabled for dev mode")
            return True

        if not self._is_continuous_monitor_alert_send_subclass():
            self.logger.warning(
                "email handler not initialized because this is not a "
                "ContinuousMonitorAlertSend subclass"
            )
            return True

        return False

    # Issue with PyEmailer 1.8.5 causes the base version to disable email handler
    #  (issue with check for setup_email_handler attr) - below is a functional work around
    def email_handler_init(self, **kwargs):
        logger_class = kwargs.get('logger_class', self.logger_class)
        try:
            if self._should_skip_email_handler_init():
                return
            logger_class.setup_email_handler(email_msg=self.email,
                                             logger_admins=self.__class__.ADMIN_EMAIL_LOGGER)
            self.email = self.initialize_new_email()
            self.logger.info("email handler initialized, initialized a new email object for use by monitor")
        except AttributeError as e:
            self.logger.error(f"email handler not initialized because {e}")
            pass

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
