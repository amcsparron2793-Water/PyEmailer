from logging import Filter, DEBUG, ERROR, Handler, FileHandler, StreamHandler, Logger, WARNING
from pathlib import Path
from typing import Union

from EasyLoggerAJM import EasyLogger, OutlookEmailHandler, StreamHandlerIgnoreExecInfo
from PyEmailerAJM.msg import Msg
from PyEmailerAJM import __project_name__, __project_root__


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


class PyEmailerLogger(EasyLogger):
    ROOT_LOG_LOCATION_DEFAULT = Path(__project_root__, 'logs').resolve()

    def __call__(self):
        return self.logger

    @staticmethod
    def _add_dupe_debug_to_handler(handler: Handler):
        dupe_debug_filter = DupeDebugFilter()
        handler.addFilter(dupe_debug_filter)

    def initialize_logger(self, logger=None, **kwargs) -> Union[Logger, '_EasyLoggerCustomLogger']:
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
        try:
            # noinspection PyTypeChecker
            email_handler = OutlookEmailHandler(email_msg=kwargs.get('email_msg', None),
                                                project_name=self.project_name,
                                                logger_dir_path=self.log_location,
                                                recipient=kwargs.get('logger_admins', None))
        except ValueError as e:
            self.logger.error(e.args[0], exc_info=True)
            raise e from None

        email_handler.setLevel(ERROR)
        email_handler.setFormatter(self.formatter)
        self.logger.addHandler(email_handler)

    def _add_filter_to_file_handler(self, handler: FileHandler):
        self._add_dupe_debug_to_handler(handler)

    def _add_filter_to_stream_handler(self, handler: StreamHandler):
        self._add_dupe_debug_to_handler(handler)

    @property
    def project_name(self):
        return super().project_name

    @project_name.setter
    def project_name(self, value):
        if value is None:
            value = __project_name__
        super().__setattr__('_project_name', value)

    def create_stream_handler(self, log_level_to_stream=WARNING, **kwargs):
        stream_handler = kwargs.get('stream_handler_instance', StreamHandlerIgnoreExecInfo())
        super().create_stream_handler(log_level_to_stream=log_level_to_stream,
                                      stream_handler_instance=stream_handler, **kwargs)