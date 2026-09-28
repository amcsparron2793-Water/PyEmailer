from __future__ import annotations

from logging import Logger
from typing import Callable

from win32.lib.pywintypes import com_error
from win32com import client as win32

from PyEmailerAJM.msg.msg import Msg
from PyEmailerAJM.backend import PyEmailerTheSandman, RPCDownError, PyEmailerLogger


class EmailerHelperClasses:
    DEFAULT_SLEEP_TIMER_CLASS = PyEmailerTheSandman

    @classmethod
    def _setup_sleep_timer_helper(cls, **kwargs) -> PyEmailerTheSandman:
        logger = kwargs.pop('logger', None)
        sleep_timer_class = kwargs.pop('sleep_timer', cls.DEFAULT_SLEEP_TIMER_CLASS)

        sleep_time_seconds = kwargs.pop('sleep_time_seconds', None)
        sleep_timer = sleep_timer_class(sleep_time_seconds=sleep_time_seconds,
                                        logger=logger, **kwargs)
        if isinstance(logger, Logger):
            logger.info(f"sleep_timer initialized")
        return sleep_timer

    @classmethod
    def initialize_helper_classes(cls, **kwargs) -> tuple[PyEmailerTheSandman, ...]:
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
        sleep_timer = cls._setup_sleep_timer_helper(logger=logger, **kwargs)
        return (sleep_timer,)


class EmailerInitializer:
    """
        A class responsible for initializing and handling email-related operations through a specified
        email application and namespace. The class uses COM (Component Object Model) to interact with
        the email application and provides mechanisms for logging and email management.

        Attributes:
            DEFAULT_EMAIL_APP_NAME (str): Default application name for email, set to 'outlook.application'.
            DEFAULT_NAMESPACE_NAME (str): Default namespace name for the email application, set to 'MAPI'.
    """
    DEFAULT_EMAIL_APP_NAME = 'outlook.application'
    DEFAULT_NAMESPACE_NAME = 'MAPI'
    HELPER_CLASSES_CLASS = EmailerHelperClasses

    def __init__(self, display_window: bool,
                 send_emails: bool, logger: Logger = None,
                 auto_send: bool = False,
                 email_app_name: str = DEFAULT_EMAIL_APP_NAME,
                 namespace_name: str = DEFAULT_NAMESPACE_NAME, **kwargs):

        self.logger, self.logger_class = self.initialize_emailer_logger(logger, **kwargs)
        self.sleep_timer = self.__class__.HELPER_CLASSES_CLASS.initialize_helper_classes(
            logger=self.logger, **kwargs)[-1]

        self.email_app_name = email_app_name
        self.namespace_name = namespace_name

        self.email_app, self.namespace, self.email = self.initialize_email_item_app_and_namespace()

        self.display_window = display_window
        self.auto_send = auto_send
        self.send_emails = send_emails

    @staticmethod
    def _py_to_html_breaks(text: str):
        return text.replace('\n', '<br>')

    @staticmethod
    def _html_to_py_breaks(text: str):
        return text.replace('<br>', '\n')

    def _handle_com_error(self, err: com_error, **kwargs):
        raise_other_error = kwargs.get('raise_other_error', True)
        rpc_down_string = "The RPC server is unavailable"
        try:
            is_rpc_down_error = rpc_down_string in err.args[1]
        except (IndexError, TypeError):
            is_rpc_down_error = rpc_down_string in err.args[0]

        if is_rpc_down_error:
            self._handle_rpc_down_com_error(err, **kwargs)
        else:
            self.logger.exception(err)
            if raise_other_error:
                raise err
            return

    def _handle_rpc_down_com_error(self, err: com_error, **kwargs):
        called_from = kwargs.get('called_from', 'unknown')
        method_to_retry = getattr(self, called_from, None)
        retry = kwargs.get('retry', False)

        self.sleep_timer.sleep_time = 30
        try:
            raise RPCDownError(sleep_time=self.sleep_timer.sleep_time) from None
        except RPCDownError as e:
            self.logger.error(e)
            self.sleep_timer.sleep_in_rounds()
            if retry and isinstance(method_to_retry, Callable):
                method_to_retry()
            elif retry and not isinstance(method_to_retry, Callable):
                raise ValueError(f"Invalid method_to_retry: {method_to_retry}")
            return

    def _reinit_sleep_time_value(self):
        sleep_time_init_value = getattr(self.sleep_timer, '_init_sleep_time_given',
                                        self.sleep_timer.__class__.DEFAULT_SLEEP_TIME_SECONDS)
        if sleep_time_init_value != self.sleep_timer.sleep_time:
            self.logger.debug(f"resetting sleep timer to: {sleep_time_init_value}")
            self.sleep_timer.sleep_time = sleep_time_init_value

    def initialize_emailer_logger(self, logger: Logger = None, **kwargs):
        if logger:
            # If a real logger instance was provided (has .info), use it directly
            if hasattr(logger, 'info') and hasattr(logger, 'warning'):
                self.logger = logger
                self.logger_class = logger.__class__
            # If a callable/factory was provided, call it to get the logger instance
            elif callable(logger):
                self.logger_class = logger
                self.logger = self.logger_class()
            else:
                # Fallback: treat as an instance but avoid calling missing methods here
                self.logger = logger
                # Derive a class reference best-effort
                self.logger_class = getattr(logger, '__class__', type(logger))
        else:
            self.logger_class = PyEmailerLogger(**kwargs)
            self.logger = self.logger_class()
        return self.logger, self.logger_class

    def initialize_new_email(self):
        if hasattr(self, 'email_app') and self.email_app is not None:
            try:
                # if not self._has_errored:
                # raise com_error(-2147023174, "The RPC server is unavailable.", None, None)
                self.email = Msg(self.email_app.CreateItem(0), logger=self.logger)
            except com_error as e:
                self._handle_com_error(err=e)
            self._reinit_sleep_time_value()
            return self.email
        raise AttributeError("email_app is not defined. Run 'initialize_email_item_app_and_namespace' first")

    def initialize_email_item_app_and_namespace(self):
        email_app, namespace, email = None, None, None
        try:
            email_app, namespace = self._setup_email_app_and_namespace()
            email = self.initialize_new_email()
        except com_error as e:
            self._handle_com_error(err=e)
        return email_app, namespace, email

    def _setup_email_app_and_namespace(self):
        self.email_app = win32.Dispatch(self.email_app_name)

        self.logger.debug(f"{self.email_app_name} app in use.")
        self.namespace = self.email_app.GetNamespace(self.namespace_name)

        self.logger.debug(f"{self.namespace_name} namespace in use.")
        return self.email_app, self.namespace
