from abc import abstractmethod
from collections.abc import Callable, Iterable
from typing import List, Dict, Type, Optional

from win32com.client import CDispatch

from PyEmailerAJM.backend import PyEmailerLogger


# noinspection PyAbstractClass
class BaseSearcher:
    # Global registry of searchers keyed by SEARCH_TYPE
    _REGISTRY: Dict[str, Type['BaseSearcher']] = {}

    SEARCH_TYPE: str | None = None  # subclasses set this to a unique key (e.g. 'subject')
    SEARCHING_STRING = "Searching for Messages..."  # partial match ok: {partial_match_ok}"

    # NEW: class-level default that can be set once for all instances
    _DEFAULT_GET_MESSAGES: Optional[Callable[..., Iterable]] = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Auto-register any subclass that defines a SEARCH_TYPE
        if getattr(cls, 'SEARCH_TYPE', None):
            key = cls.SEARCH_TYPE.lower()
            BaseSearcher._REGISTRY[key] = cls

    def __init__(self, logger=None, *, get_messages: Callable[..., Iterable] | None = None, **kwargs):
        self._searching_string = None
        if logger:
            self.logger = logger
        else:
            self._elog = PyEmailerLogger(**kwargs)
            self.logger = self._elog()

        # Instance provider, if not provided, fall back to class default
        self._get_messages = get_messages or self.__class__._DEFAULT_GET_MESSAGES
        if self._get_messages is None:
            # Not fatal immediately; we raise only if someone calls GetMessages without a provider
            self.logger.debug("No get_messages provider set yet; call set_default_get_messages or pass get_messages.")

    @abstractmethod
    def find_messages_by_attribute(self, search_str: str, partial_match_ok: bool = False, **kwargs) -> List[CDispatch]:
        ...

    @classmethod
    def set_default_get_messages(cls, provider: Callable[..., Iterable]) -> None:
        """Set a global default provider for all searchers (current and future instances).
        Typically provider = py_emailer.GetMessages.
        """
        cls._default_get_messages = provider

    def GetMessages(self, *args, **kwargs):
        if not self._get_messages:
            raise NotImplementedError(
                "No GetMessages provider configured. Pass get_messages=... to the constructor "
                "or call BaseSearcher.set_default_get_messages(py_emailer.GetMessages)."
            )
        return self._get_messages(*args, **kwargs)

    @classmethod
    def get_attribute_for_search(cls, message: CDispatch, attribute: str):
        return getattr(message, attribute, getattr(message(), attribute, None))

    @property
    def searching_string(self):
        return self._searching_string

    @searching_string.setter
    def searching_string(self, value: str):
        self._searching_string = value

    def get_normalized_attr_and_candidate(self, message: CDispatch, attribute: str, search_str: str):
        normalized_message_attr = self._normalize_to_string(
            BaseSearcher.get_attribute_for_search(
                message, attribute)
        )
        normalized_search_str = self._normalize_to_string(search_str)
        # print(normalized_message_attr, normalized_search_str)
        return normalized_message_attr, normalized_search_str

    def fetch_matched_messages(self, search_string: str, msg_attr_name: str,
                               partial_match_ok: bool = False, **kwargs):
        matched_messages = []
        for message in self.GetMessages():
            (normalized_msg_attr,
             normalized_search_string) = self.get_normalized_attr_and_candidate(message,
                                                                                msg_attr_name,
                                                                                search_string)
            # normalized_msg_attr = str(getattr(message(), normalized_msg_attr_name))
            self.logger.debug(f"got attribute {msg_attr_name} with value {normalized_msg_attr}")
            msg = self._search_for_match(search_string, message, normalized_msg_attr,
                                         partial_match_ok, **kwargs)
            if msg:
                matched_messages.append(msg)
                continue
        self.logger.info(f"{len(matched_messages)} messages found!")  #, print_msg=True)
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
    def _normalize_to_string(raw_string: str) -> str:
        """Normalize the given str by converting to lowercase and stripping whitespace."""
        return str(raw_string).lower().strip()

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


class AttributeSearcher(BaseSearcher):
    """ Generic searcher for a specific outlook item attribute. """

    def __init__(self, attribute: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attribute = attribute  # body, SenderName etc

    def find_messages_by_attribute(self, search_str: str, partial_match_ok: bool = False, **kwargs) -> List[CDispatch]:
        """Returns a list of messages matching the given attribute."""
        self.searching_string = f"Searching for Messages with {self._attribute} containing \'{search_str}\'"
        self.logger.info(self.searching_string, print_msg=True)
        return self.fetch_matched_messages(search_str, self._attribute, partial_match_ok, **kwargs)


class SubjectSearcher(BaseSearcher):
    # Constants for prefixes
    FW_PREFIXES = ['FW:', 'FWD:']
    RE_PREFIX = 'RE:'
    SEARCHING_STRING = ("searching for messages with subject \'{search_subject}\' "
                        "partial match ok: {partial_match_ok}").capitalize()
    SEARCH_TYPE = 'subject'

    # FIXME: this gets the attribute value passed in already formed etc
    #  - attribute value should not be passed in directly
    def _search_for_match(self, search_str: str, message: CDispatch,
                          attribute: str, partial_match_ok: bool = False,
                          **kwargs):
        include_fw = kwargs.get('include_fw', True)
        include_re = kwargs.get('include_re', True)
        # FIXME: this is a bandaid - attribute value should not be passed in directly
        normalized_message_attr = self._normalize_to_string(attribute)
        normalized_search_str = self._normalize_to_string(search_str)
        # (normalized_message_attr,
        #  normalized_search_str) = self.get_normalized_attr_and_candidate(message, attribute, search_str)

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
        return None

    def find_messages_by_attribute(self, search_str: str, partial_match_ok: bool = False, **kwargs) -> List[CDispatch]:
        """ Acts as a wrapper for self.find_messages_by_subject """
        return self.find_messages_by_subject(search_str, partial_match_ok=partial_match_ok, **kwargs)

    def find_messages_by_subject(self, search_subject: str, msg_attr: str = 'subject',
                                 partial_match_ok: bool = False, **kwargs) -> List[CDispatch]:
        """Returns a list of messages matching the given subject, ignoring prefixes based on flags."""

        # # Normalize the search subject and msg attr
        # normalized_subject = self._normalize_to_string(search_subject)
        # normalized_msg_attr = self._normalize_to_string(msg_attr)
        # print(normalized_subject, normalized_msg_attr)

        self.searching_string = self.__class__.SEARCHING_STRING.format(search_subject=search_subject,
                                                                       partial_match_ok=partial_match_ok)
        self.logger.info(self.searching_string, print_msg=True)

        return self.fetch_matched_messages(search_subject, msg_attr, **kwargs)

    def _matches_prefix(self, message_subject: str, prefixes: list, search_subject: str,
                        partial_match_ok: bool = False) -> bool:
        """Checks if the message subject matches the search subject after removing a prefix."""
        for prefix in prefixes:
            if message_subject.startswith(prefix.lower()):
                stripped_subject = message_subject.split(prefix.lower(), 1)[1].strip()
                return (self._is_exact_match(stripped_subject, search_subject) if not partial_match_ok
                        else self._is_partial_match(stripped_subject, search_subject))
        return False
