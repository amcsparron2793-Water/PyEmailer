import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional, List
from logging import getLogger, basicConfig, getLevelName, INFO, DEBUG


if TYPE_CHECKING:
    from logging import Logger


class SnoozeTracking:
    """
    Represents tracking functionality for snoozed messages, allowing saving, loading, and managing their states.

    Methods:
        __init__(file_path, **kwargs):
            Initializes the SnoozeTracking instance with the specified file path and optional logger configuration.

        json_loaded:
            Property that loads and retrieves the JSON data from the file. If the file doesn’t exist, an empty dictionary is returned.

        init_logger(log_level=INFO, **kwargs):
            Initializes and configures the logger. If a logger is not provided, it creates one with basic configuration.

        write_entry(email_subject, snooze_time):
            Writes a new snooze entry with the given email subject and snooze time. Prevents overwriting if a newer snooze time exists.

        _convert_datetime(value):
            Converts a datetime object to its ISO 8601 string format. For non-datetime values, it simply returns the value.

        save_json():
            Saves the current JSON data to the specified file path in a formatted structure.

        read_entry(email_subject):
            Retrieves and returns the snooze time for the provided email subject as a datetime object. Returns None if no entry exists.

        snooze_msgs(msg_list):
            Processes a list of messages, marking non-snoozed messages as snoozed and writing entries for them. Raises an exception if a message doesn’t have the required properties.
    """
    def __init__(self, file_path: Path, **kwargs):
        self.logger = self.init_logger(**kwargs)
        self.file_path = file_path
        self._json_loaded = None
        self.logger.info(f"{self.__class__.__name__} loaded")

    @property
    def json_loaded(self):
        """
        Returns the JSON-loaded data. If the data has not been loaded yet, it attempts to load it from a file located at `file_path`.
        If the file does not exist, it initializes and returns an empty dictionary.

        :return: The loaded JSON data or an empty dictionary if the file is not found.
        :rtype: dict
        """
        if self._json_loaded is None:
            if self.file_path.is_file():
                with open(self.file_path, 'r') as f:
                    self._json_loaded = json.load(f)
                    self.logger.info(f"json loaded from {self.file_path}")
            else:
                self.logger.info("no json loaded, returning new dictionary")
                self._json_loaded = {}
        return self._json_loaded

    @property
    def num_snoozed_msgs(self):
        if self.json_loaded and hasattr(self.json_loaded, '__len__'):
            return len(self.json_loaded)
        else:
            return 0

    def init_logger(self, log_level=INFO, **kwargs):
        """
        :param log_level: The logging level to be set for the logger if no logger is provided. Default is `INFO`.
        :type log_level: int
        :param kwargs: Additional keyword arguments. Accepts 'logger' for a pre-configured logger and 'logger_name' for the logger's name.
        :type kwargs: dict
        :return: A logger instance based on the provided or created configuration.
        :rtype: Logger or None
        """
        self.logger: Optional[Logger] = kwargs.get('logger', None)
        logger_name = kwargs.get('logger_name', 'logger')

        if self.logger is None:
            self.logger = getLogger(logger_name)#self.__class__.__name__)
            if self.logger.hasHandlers():
                self.logger.debug(
                    f"logger '{logger_name}' with level "
                    f"{getLevelName(self.logger.getEffectiveLevel())} "
                    f"already exists, "
                    f"skipping creation of new logger")
                pass
            else:
                basicConfig(level=log_level)
                self.logger.warning(f"no logger provided, using basicConfig with level: {log_level}.")
        return self.logger

    def write_entry(self, email_subject: str, snooze_time: datetime):
        """
        :param email_subject: The subject of the email to be logged or updated.
        :type email_subject: str
        :param snooze_time: The datetime until which the email is snoozed.
        :type snooze_time: datetime
        :return: None
        :rtype: None
        """
        if (self.json_loaded.get(email_subject, None) is not None
                and snooze_time < datetime.fromisoformat(self.json_loaded[email_subject])):
            self.logger.warning(f"entry already exists, (snoozed at {snooze_time}) skipping write...")
            return
        self.json_loaded.update({email_subject: snooze_time})
        self.logger.debug(f'email_subject ({email_subject}) '
                          f'written with a snooze time of {snooze_time}')
        self.save_json()

    @staticmethod
    def _convert_datetime(value) -> str:
        """
        Converts a datetime object to an ISO 8601 formatted string. If the input value is not a datetime object, returns the value unchanged.

        :param value: The value to be converted, which can be a datetime object or any other data type.
        :type value: Any
        :return: An ISO 8601 formatted string if the input is a datetime object, otherwise returns the original value.
        :rtype: str
        """
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    def save_json(self):
        """
        Saves the current state of the JSON data to a file specified by `self.file_path`.
        The method serializes the JSON data and writes it to a file using an indentation of 4 spaces.
        If there are datetime objects in the data, they are converted using the `_convert_datetime` method.
        Logs the operation upon success.

        :return: None
        :rtype: None
        """
        with open(self.file_path, 'w') as f:
            # noinspection PyTypeChecker
            json.dump(self.json_loaded, f, indent=4, default=self._convert_datetime)
            self.logger.info(f"json saved to {self.file_path}")

    def read_entry(self, email_subject: str):
        """
        :param email_subject: The subject of the email used to retrieve the corresponding entry from the JSON data.
        :type email_subject: str
        :return: A datetime object parsed from the entry corresponding to the email subject or None if the entry does not exist.
        :rtype: Optional[datetime]
        """
        entry: Optional[str] = self.json_loaded.get(email_subject, None)
        if entry is None:
            self.logger.debug(f"no entry for {email_subject}")
            return None
        self.logger.debug(f"{email_subject} retrieved")
        return datetime.fromisoformat(str(entry))

    def snooze_msgs(self, msg_list: List['_AlertMsgBase']):
        """
        :param msg_list: A list of message objects that need to be snoozed. Each message object should have the attributes `msg_snoozed`, `subject`, and `msg_snoozed_time`.
        :type msg_list: List[_AlertMsgBase]
        :return: Returns the updated list of messages after processing snooze operations.
        :rtype: List[_AlertMsgBase]
        """
        for m in msg_list:
            if not hasattr(m, 'msg_snoozed'):
                try:
                    raise AttributeError(f"msg_snoozed not found in {m}")
                except AttributeError as e:
                    self.logger.error(e, exc_info=True)
                    raise e
            if not m.msg_snoozed:
                m.msg_snoozed = True
                self.write_entry(m.subject, m.msg_snoozed_time)
            else:
                print(f"{m.subject} already marked as snoozed")
        return msg_list
