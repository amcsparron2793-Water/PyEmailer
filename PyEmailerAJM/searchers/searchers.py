from abc import abstractmethod
from typing import List

from win32com.client import CDispatch

from PyEmailerAJM.backend import PyEmailerLogger


class BaseSearcher:
    SEARCHING_STRING = "Searching for Messages..."  #partial match ok: {partial_match_ok}"

    def __init__(self, logger, **kwargs):
        self._searching_string = None
        if logger:
            self.logger = logger
        else:
            self._elog = PyEmailerLogger(**kwargs)
            self.logger = self._elog()

    @abstractmethod
    def GetMessages(self):
        ...

    @classmethod
    def get_attribute_for_search(cls, message: CDispatch, attribute: str):
        if hasattr(message, attribute):
            return getattr(message, attribute)

    @property
    def searching_string(self):
        return self._searching_string

    @searching_string.setter
    def searching_string(self, value: str):
        self._searching_string = value

    def get_normalized_attr_and_candidate(self, message: CDispatch, attribute: str, search_str: str):
        normalized_message_attr = self._normalize_string(BaseSearcher.get_attribute_for_search(message, attribute))
        normalized_search_str = self._normalize_string(search_str)
        return normalized_message_attr, normalized_search_str

    def fetch_matched_messages(self, normalized_search_string: str, normalized_msg_attr: str,
                               partial_match_ok: bool = False, **kwargs):
        matched_messages = []
        for message in self.GetMessages():
            msg = self._search_for_match(normalized_search_string, message, normalized_msg_attr,
                                         partial_match_ok, **kwargs)
            if msg:
                matched_messages.append(msg)
                continue
        self.logger.info(f"{len(matched_messages)} messages found!")#, print_msg=True)
        self.logger.info("Search Complete, returning Msg's")
        return [m() for m in matched_messages]

    def _search_for_match(self, normalized_search_str: str, message: CDispatch, normalized_message_attr: str,
                          partial_match_ok: bool = False, **kwargs):
        if (self._is_exact_match(normalized_search_str, normalized_message_attr) or
                (partial_match_ok and self._is_partial_match(normalized_search_str,
                                                             normalized_message_attr))):
            return message
        return None

    @staticmethod
    def _normalize_string(raw_string: str) -> str:
        """Normalize the given str by converting to lowercase and stripping whitespace."""
        return raw_string.lower().strip()

    @staticmethod
    def _is_exact_match(candidate_str: str, search_str: str) -> bool:
        """Checks if the subject matches exactly."""
        if candidate_str == '' or search_str == '':
            return False
        return candidate_str == search_str

    @staticmethod
    def _is_partial_match(candidate_str: str, search_str: str) -> bool:
        if candidate_str == '' or search_str == '':
            return False
        return search_str in candidate_str


class SubjectSearcher(BaseSearcher):
    # Constants for prefixes
    FW_PREFIXES = ['FW:', 'FWD:']
    RE_PREFIX = 'RE:'
    SEARCHING_STRING = ("searching for messages with subject \'{search_subject}\' "
                        "partial match ok: {partial_match_ok}").capitalize()

    @abstractmethod
    def GetMessages(self):
        ...

    def _search_for_match(self, search_str: str, message: CDispatch,
                          attribute: str, partial_match_ok: bool = False,
                          **kwargs):
        include_fw = kwargs.get('include_fw', True)
        include_re = kwargs.get('include_re', True)

        (normalized_message_attr,
         normalized_search_str) = self.get_normalized_attr_and_candidate(message, attribute, search_str)

        if super()._search_for_match(normalized_search_str, message,
                                     normalized_message_attr, partial_match_ok):
            return message

        if include_fw and self._matches_prefix(normalized_search_str,
                                               self.__class__.FW_PREFIXES,
                                               normalized_message_attr,
                                               partial_match_ok):
            return message
        if include_re and self._matches_prefix(normalized_search_str,
                                               [self.__class__.RE_PREFIX],
                                               normalized_message_attr,
                                               partial_match_ok):
            return message

    def find_messages_by_subject(self, search_subject: str, msg_attr: str = 'subject',
                                 partial_match_ok: bool = False, **kwargs) -> List[CDispatch]:
        """Returns a list of messages matching the given subject, ignoring prefixes based on flags."""

        # Normalize search subject
        normalized_subject = self._normalize_string(search_subject)
        normalized_msg_attr = self._normalize_string(msg_attr)

        self.searching_string = self.__class__.SEARCHING_STRING.format(search_subject=search_subject,
                                                                       partial_match_ok=partial_match_ok)
        self.logger.info(self.searching_string, print_msg=True)

        return self.fetch_matched_messages(normalized_subject, normalized_msg_attr, **kwargs)

    def _matches_prefix(self, message_subject: str, prefixes: list, search_subject: str,
                        partial_match_ok: bool = False) -> bool:
        """Checks if the message subject matches the search subject after removing a prefix."""
        for prefix in prefixes:
            if message_subject.startswith(prefix.lower()):
                stripped_subject = message_subject.split(prefix.lower(), 1)[1].strip()
                return (self._is_exact_match(stripped_subject, search_subject) if not partial_match_ok
                        else self._is_partial_match(stripped_subject, search_subject))
        return False
