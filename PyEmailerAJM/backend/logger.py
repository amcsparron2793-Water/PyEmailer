import logging
from logging import Filter, DEBUG, ERROR, Handler, FileHandler, StreamHandler
from typing import Union

from EasyLoggerAJM import EasyLogger, OutlookEmailHandler, _EasyLoggerCustomLogger
from PyEmailerAJM.msg import Msg


class DupeDebugFilter(Filter):
    PREFIXES_TO_IGNORE = ["FW:", "RE:"]

    def __init__(self, name="DebugDedupeFilter"):
        super().__init__(name)
        self.logged_messages = set()

    def _clean_str(self, in_str):
        for x in self.__class__.PREFIXES_TO_IGNORE:
            in_str = in_str.replace(x, '')
        return in_str

    def filter(self, record):
        # We only log the message if it has not been logged before
        if record.levelno != DEBUG:
            return True
        clean_msg = self._clean_str(record.msg)
        if clean_msg not in list(self.logged_messages):
            self.logged_messages.add(clean_msg)
            return True
        return False


class PyEmailerCustomLogger(_EasyLoggerCustomLogger):
    @staticmethod
    def sanitize_msg(msg):
        # try:
        msg = msg.encode('cp1250', errors='ignore').decode('cp1250')
        # except UnicodeEncodeError as e:
        #     msg = msg.encode('ascii', errors='ignore')
        #     print(f"msg was not CP1252, converted to utf-8: {msg}")
        return msg

    def info(self, msg: object, *args: object, exc_info=None,
             stack_info: bool = False, stacklevel: int = 1,
             extra=None, **kwargs):
        msg = self.sanitize_msg(msg)
        super().info(msg, *args, exc_info=exc_info,
                     stack_info=stack_info, stacklevel=stacklevel,
                     extra=extra, **kwargs)

    def warning(self, msg: object, *args: object, exc_info=None,
                stack_info: bool = False, stacklevel: int = 1,
                extra=None, **kwargs):
        msg = self.sanitize_msg(msg)
        super().warning(msg, *args, exc_info=exc_info,
                        stack_info=stack_info, stacklevel=stacklevel,
                        extra=extra, **kwargs)

    def error(self, msg: object, *args: object, exc_info=None,
              stack_info: bool = False, stacklevel: int = 1,
              extra=None, **kwargs):
        msg = self.sanitize_msg(msg)
        super().error(msg, *args, exc_info=exc_info,
                      stack_info=stack_info, stacklevel=stacklevel,
                      extra=extra, **kwargs)

    def debug(self, msg: object, *args: object, exc_info=None,
              stack_info: bool = False, stacklevel: int = 1,
              extra=None, **kwargs):
        msg = self.sanitize_msg(msg)
        super().debug(msg, *args, exc_info=exc_info,
                      stack_info=stack_info, stacklevel=stacklevel,
                      extra=extra, **kwargs)

    def critical(self, msg: object, *args: object, exc_info=None,
                 stack_info: bool = False, stacklevel: int = 1,
                 extra=None, **kwargs):
        msg = self.sanitize_msg(msg)
        super().critical(msg, *args, exc_info=exc_info,
                         stack_info=stack_info, stacklevel=stacklevel,
                         extra=extra, **kwargs)


class PyEmailerLogger(EasyLogger):
    def __call__(self):
        return self.logger

    @staticmethod
    def _add_dupe_debug_to_handler(handler: Handler):
        dupe_debug_filter = DupeDebugFilter()
        handler.addFilter(dupe_debug_filter)

    def _set_logger_class(self, logger_class=PyEmailerCustomLogger, **kwargs):
        return super()._set_logger_class(logger_class=logger_class, **kwargs)

    def initialize_logger(self, logger=None, **kwargs) -> Union[logging.Logger, _EasyLoggerCustomLogger]:
        self.logger = super().initialize_logger(logger=logger, **kwargs)
        self.logger.propagate = False
        return self.logger

    def setup_email_handler(self, **kwargs):
        """
        Sets up the email handler for the logger using the OutlookEmailHandler.

        :param kwargs: Keyword arguments to configure the email handler.
                       - email_msg: Specifies the email message content (default: None).
                       - logger_admins: Specifies the list of admin emails (default: None).
        :return: None
        :rtype: None
        """
        # noinspection PyTypeChecker
        OutlookEmailHandler.VALID_EMAIL_MSG_TYPES = [Msg]

        # noinspection PyTypeChecker
        email_handler = OutlookEmailHandler(email_msg=kwargs.get('email_msg', None),
                                            project_name=self.project_name,
                                            logger_dir_path=self.log_location,
                                            recipient=kwargs.get('logger_admins', None))
        email_handler.setLevel(ERROR)
        email_handler.setFormatter(self.formatter)
        self.logger.addHandler(email_handler)

    def _add_filter_to_file_handler(self, handler: FileHandler):
        self._add_dupe_debug_to_handler(handler)

    def _add_filter_to_stream_handler(self, handler: StreamHandler):
        self._add_dupe_debug_to_handler(handler)
