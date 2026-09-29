from logging import Filter, DEBUG, ERROR, Handler, FileHandler, StreamHandler, Logger, WARNING
from typing import Union, TYPE_CHECKING

from EasyLoggerAJM import EasyLogger
from EasyLoggerAJM.logger_parts import OutlookEmailHandler, StreamHandlerIgnoreExecInfo
from PyEmailerAJM.msg import Msg

# noinspection PyUnresolvedReferences
from pythoncom import com_error

if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from EasyLoggerAJM.easy_logger import _EasyLoggerCustomLogger


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


class PyEmailerOutlookEmailHandler(OutlookEmailHandler):
    APP_CAUSED_ERROR_ERR_CODE = -2147352567
    MOVED_OR_DELETED_MSG_ERR_CODE = -2147221238
    VALID_EMAIL_MSG_TYPES = [Msg]

    def get_real_com_error(self, err: com_error):
        if len(err.args) >= 3 and err.args[0] == self.__class__.APP_CAUSED_ERROR_ERR_CODE:
            excepinfo = err.args[2]

            if len(excepinfo) >= 6:
                return excepinfo[5], excepinfo[2]

        return err.args[0], err.args[1]

    def _use_error_template(self, err: com_error, **kwargs):
        real_err_tuple = self.get_real_com_error(err)
        msg_moved = real_err_tuple[0] == self.__class__.MOVED_OR_DELETED_MSG_ERR_CODE
        if msg_moved:
            return
    # FIXME: msg_moved bug is d/t the finally block in emit always resending even when it isn't needed.
    #  This is a workaround.


class PyEmailerLogger(EasyLogger):
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
        email_handler_class = kwargs.get('email_handler_class', PyEmailerOutlookEmailHandler)
        # noinspection PyTypeChecker
        email_handler_class.VALID_EMAIL_MSG_TYPES = [Msg]
        try:
            # noinspection PyTypeChecker
            email_handler = email_handler_class(email_msg=kwargs.get('email_msg', None),
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

    def create_stream_handler(self, log_level_to_stream=WARNING, **kwargs):
        stream_handler = kwargs.get('stream_handler_instance', StreamHandlerIgnoreExecInfo())
        super().create_stream_handler(log_level_to_stream=log_level_to_stream,
                                      stream_handler_instance=stream_handler, **kwargs)
