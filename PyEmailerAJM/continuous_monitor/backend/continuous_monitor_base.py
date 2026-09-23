from abc import abstractmethod
from logging import Logger
from os import getenv
from pathlib import Path
from typing import TYPE_CHECKING, Optional, List, Union, Callable

from PyEmailerAJM import PyEmailer, is_instance_of_dynamic
from PyEmailerAJM.backend import PyEmailerTheSandman
from . import ContinuousColorizer, SnoozeTracking, EmailState

if TYPE_CHECKING:
    from PyEmailerAJM.backend import AlertTypes


class _HelperClasses:
    """
    Provides a set of default helper class factories and methods for managing and
    initializing snooze trackers, colorizers, and sleep timers.

    This class defines factory methods and configuration helpers for creating instances
    of default or custom implementations of specific utility classes. It is designed to
    simplify the initialization process while keeping the customization options flexible
    via keyword arguments.

    :ivar DEFAULT_SNOOZE_TRACKER_CLASS: Default class used to initialize snooze tracker helper.
    :type DEFAULT_SNOOZE_TRACKER_CLASS: type
    :ivar DEFAULT_COLORIZER_CLASS: Default class used to initialize colorizer helper.
    :type DEFAULT_COLORIZER_CLASS: type
    :ivar DEFAULT_SLEEP_TIMER_CLASS: Default class used to initialize sleep timer helper.
    :type DEFAULT_SLEEP_TIMER_CLASS: type
    """
    DEFAULT_SNOOZE_TRACKER_CLASS = SnoozeTracking
    DEFAULT_COLORIZER_CLASS = ContinuousColorizer
    DEFAULT_SLEEP_TIMER_CLASS = PyEmailerTheSandman

    @classmethod
    def _setup_snooze_tracker_helper(cls, **kwargs):
        logger = kwargs.pop('logger', None)
        snooze_file_path = kwargs.pop('snooze_file_path', './snooze_tracker.json')
        snooze_file_path = Path(snooze_file_path)

        snooze_tracker_class = kwargs.pop('snooze_tracker', cls.DEFAULT_SNOOZE_TRACKER_CLASS)
        snooze_tracker = snooze_tracker_class(file_path=snooze_file_path, logger=logger, **kwargs)
        if isinstance(logger, Logger):
            logger.info(f"snooze_tracker initialized, tracking snoozed emails in: {snooze_tracker.file_path}")
        return snooze_tracker

    @classmethod
    def _setup_colorizer_helper(cls, **kwargs):
        logger = kwargs.pop('logger', None)
        colorizer_class = kwargs.pop('colorizer', cls.DEFAULT_COLORIZER_CLASS)
        colorizer = colorizer_class(logger=logger, **kwargs)
        if isinstance(logger, Logger):
            logger.info(f"colorizer initialized")
        return colorizer

    @classmethod
    def _setup_sleep_timer_helper(cls, **kwargs):
        logger = kwargs.pop('logger', None)
        sleep_timer_class = kwargs.pop('sleep_timer', cls.DEFAULT_SLEEP_TIMER_CLASS)

        sleep_time_seconds = kwargs.pop('sleep_time_seconds', None)
        sleep_timer = sleep_timer_class(sleep_time_seconds=sleep_time_seconds,
                                        logger=logger, **kwargs)
        if isinstance(logger, Logger):
            logger.info(f"sleep_timer initialized")
        return sleep_timer

    @classmethod
    def initialize_helper_classes(cls, **kwargs):
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

        logger = kwargs.pop('logger', None)

        # Extract helper class factories with defaults
        colorizer = cls._setup_colorizer_helper(logger=logger, **kwargs)
        snooze_tracker = cls._setup_snooze_tracker_helper(logger=logger, **kwargs)
        sleep_timer = cls._setup_sleep_timer_helper(logger=logger, **kwargs)

        return colorizer, snooze_tracker, sleep_timer


class ContinuousMonitorBase(PyEmailer, EmailState):
    """
    Base class for monitoring and handling email alerts continuously.

    This class provides functionalities to monitor alerts, send email notifications,
    and manage various related components such as snooze trackers, loggers, and email handlers.
    It allows customization through class-level attributes and helper classes for extensions.

    :ivar ADMIN_EMAIL_LOGGER: A list of email addresses where admin logs are sent.
    :type ADMIN_EMAIL_LOGGER: List[str]
    :ivar ADMIN_EMAIL: A list of admin email addresses.
    :type ADMIN_EMAIL: List[str]
    :ivar ATTRS_TO_CHECK: A list of attributes that need to be verified before usage.
    :type ATTRS_TO_CHECK: List[str]
    :ivar HELPER_CLASSES_CLASS: Specifies the helper class responsible for initializing auxiliary components.
    :ivar dev_mode: Indicates whether the application is running in development mode.
    :type dev_mode: bool
    """
    ADMIN_EMAIL_LOGGER: List[str] = []
    ADMIN_EMAIL: List[str] = []
    ATTRS_TO_CHECK: List[str] = []
    HELPER_CLASSES_CLASS = _HelperClasses

    def __init__(self, display_window: bool, send_emails: bool, **kwargs):
        # Let EmailerInitializer handle logger factory vs instance normalization
        super().__init__(display_window, send_emails, **kwargs)

        self.dev_mode = kwargs.get('dev_mode', False)
        kwargs.pop('logger', None)

        (self.colorizer,
         self.snooze_tracker,
         self.sleep_timer) = self.__class__.HELPER_CLASSES_CLASS.initialize_helper_classes(logger=self.logger, **kwargs)

        self.log_dev_mode_warnings()
        self.email_handler_init()

    @property
    def num_snoozed_msgs(self):
        if getattr(self, 'snooze_tracker', None) is not None:
            if (self.snooze_tracker.json_loaded and
                    hasattr(self.snooze_tracker.json_loaded, '__len__')):
                return len(self.snooze_tracker.json_loaded)
        return 0

    @classmethod
    def check_for_class_attrs(cls, class_attrs_to_check):
        for c in class_attrs_to_check:
            if hasattr(cls, c) and isinstance(getattr(cls, c), list) and len(getattr(cls, c)) > 0:
                continue
            raise ValueError(f"{c} must be a list of email addresses")

    def _normalize_logger(self, **kwargs) -> Logger:
        # Normalize logger: if it's a factory, call it to get the instance
        logger_arg: Union[Callable, Logger] = kwargs.pop('logger', self.logger)
        if callable(logger_arg) and not hasattr(logger_arg, 'info'):
            # It's a factory, not a logger instance
            logger: Logger = logger_arg()
        else:
            logger = logger_arg
        return logger

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

    def _GetReadFolder(self, email_dir_index: int = None, **kwargs):
        """
        :param email_dir_index: Specifies the email directory index to be accessed. Defaults to None.
        :type email_dir_index: int, optional
        :param kwargs: Additional optional arguments that may be passed. Can include `subfolder_name` to specify a subfolder name.
        :type kwargs: dict
        :return: The folder specified either by the email directory index or the default folder along with the subfolder if applicable.
        :rtype: object
        """
        kwargs.setdefault('subfolder_name', self.__class__.DEFAULT_SUBFOLDER_NAME)
        if not email_dir_index:
            email_dir_index = self.__class__.DEFAULT_READ_FOLDER_NAME
        return super()._GetReadFolder(email_dir_index, **kwargs)
