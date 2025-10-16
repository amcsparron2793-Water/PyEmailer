from abc import abstractmethod
from typing import List, Iterable

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
        return (search_str in candidate_str) or (candidate_str in search_str)


class FastPathSearcher:
    FW_PREFIXES: List[str] = []
    RE_PREFIX: List[str] = []

    def __init_subclass__(cls, **kwargs):
        mandatory_attributes = ['FW_PREFIXES', 'RE_PREFIX']
        if any([x for x in mandatory_attributes if not hasattr(cls, x)]):
            raise AttributeError(f"All subclasses of FastPathSearcher must define the following attributes: "
                                 f"{', '.join(mandatory_attributes)}")
    # noinspection PyAbstractClass
    @abstractmethod
    def GetMessages(self):
        ...

    def _build_terms(self, operator, escaped, include_fw, include_re, **kwargs):
        terms = [f"[Subject] {operator} '{escaped}'"]
        if include_fw:
            for x in self.__class__.FW_PREFIXES:
                terms.append(f"[Subject] {operator} '{x} {escaped}'")
        if include_re:
            for x in self.__class__.RE_PREFIX:
                terms.append(f"[Subject] {operator} '{x} {escaped}'")
        return terms

    def _build_sql_filter(self, search_subject, partial_match_ok, **kwargs) -> str:
        # Build an @SQL filter that matches the desired subject, accounting for prefixes
        # Note: [Subject] alias is recognized by Outlook's @SQL provider
        include_fw = kwargs.get('include_fw', True)
        include_re = kwargs.get('include_re', True)

        escaped = search_subject.replace("'", "''")
        if partial_match_ok:
            self.logger.warning("Partial match is not supported with fasttrack at this time, setting to false. "
                                "\nRun with no_fastpath_search set to True for partial match searches. ")
            partial_match_ok = False

        if partial_match_ok:
            operator = 'LIKE'
            like = f"%{escaped}%"
            terms = self._build_terms(operator, like, include_fw, include_re, **kwargs)

        else:
            operator = '='
            terms = self._build_terms(operator, escaped, include_fw, include_re, **kwargs)

        sql_where = ' OR '.join(f'({t})' for t in terms) if terms else f"[Subject] = '{escaped}'"
        sql = sql_where
        self.logger.debug(f"sql filter: {sql}")
        return sql

    # noinspection PyBroadException
    def _attempt_item_sort(self, folder: CDispatch):
        items = folder.Items
        # Sorting can make Find/Restrict more reliable on some stores; optional
        try:
            items.Sort('[ReceivedTime]', True)
            self.logger.debug("Items sorted by ReceivedTime")
        except Exception:
            pass
        try:
            items.IncludeRecurrences = True
            self.logger.debug("Items include recurrences")
        except Exception:
            pass
        return items

    def _get_fastpath_search_folder(self):
        # Ensure we have a folder to search
        folder = getattr(self, 'read_folder', None)
        if folder is None and hasattr(self, '_GetReadFolder'):
            # Default to INBOX/_GetReadFolder behavior of PyEmailer
            folder = self._GetReadFolder()
            setattr(self, 'read_folder', folder)
        return folder

    # noinspection PyBroadException
    def _fastpath_search(self, items, sql: str, **kwargs):
        try:
            restricted = items.Restrict(sql)
            # Convert to list of CDispatch quickly; no Python-side filtering
            results: List[CDispatch] = []
            # Using Find/FindNext over restricted to avoid full enumeration when large
            try:
                itm = restricted.Find()
                while itm is not None:
                    results.append(itm)
                    itm = restricted.FindNext()

            except Exception:
                # Fall back to iterating the restricted collection
                for itm in restricted:
                    results.append(itm)
            self.logger.info(f"{len(results)} messages found via fast search!")
            return results

        except Exception as e:
            # If Restrict fails (e.g., older store), fall back
            self.logger.error(f"Restrict failed, falling back to Python scan: {e}", print_msg=True)
            return e

    def run_fastpath_search(self, search_subject: str, partial_match_ok: bool = False, **kwargs):
        # Try fast path using Items.Restrict if we have a read_folder (PyEmailer sets this)
        try:
            folder = self._get_fastpath_search_folder()

            if folder is not None and hasattr(folder, 'Items'):
                items = self._attempt_item_sort(folder)
                sql = self._build_sql_filter(search_subject=search_subject,
                                             partial_match_ok=partial_match_ok, **kwargs)
                results = self._fastpath_search(items, sql, **kwargs)
                if isinstance(results, Exception):
                    raise results from None
                return results or []
            raise AttributeError("No read_folder available for fast path search.")

        except Exception as e:
            # Any unexpected failure -> fall back
            self.logger.debug(f"Fast subject search preparation failed: {e}")
            return e


class SubjectSearcher(BaseSearcher, FastPathSearcher):
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
        """Returns a list of messages matching the given subject, ignoring prefixes based on flags.

        Optimization: If an Outlook read folder is available on `self` (PyEmailer provides `read_folder`),
        use Outlook's Items.Restrict/@SQL to filter by subject server-side instead of iterating Python-side.
        Falls back to the existing in-Python scan if Restrict is unavailable or throws a COM error.
        """

        # Normalize search subject and attr label
        normalized_subject = self._normalize_string(search_subject)
        normalized_msg_attr = self._normalize_string(msg_attr)

        self.searching_string = self.__class__.SEARCHING_STRING.format(search_subject=search_subject,
                                                                       partial_match_ok=partial_match_ok)
        self.logger.info(self.searching_string, print_msg=True)

        if hasattr(self, 'run_fastpath_search') and not kwargs.get('no_fastpath_search', False):
            try:
                res = self.run_fastpath_search(search_subject, partial_match_ok, **kwargs)
                if isinstance(res, Exception):
                    raise res from None
                return res
            except Exception as e:
                pass
        else:
            self.logger.warning("No fast path search available.")

        # Fallback: Python-side scan through all messages
        self.logger.warning("Falling back to Python-side scan...")
        return self.fetch_matched_messages(normalized_subject, normalized_msg_attr, partial_match_ok, **kwargs)

    def _matches_prefix(self, message_subject: str, prefixes: list, search_subject: str,
                        partial_match_ok: bool = False) -> bool:
        """Checks if the message subject matches the search subject after removing a prefix."""
        for prefix in prefixes:
            if message_subject.startswith(prefix.lower()):
                stripped_subject = message_subject.split(prefix.lower(), 1)[1].strip()
                return (self._is_exact_match(stripped_subject, search_subject) if not partial_match_ok
                        else self._is_partial_match(stripped_subject, search_subject))
        return False


# Commonly recognized Outlook @SQL aliases
# These are the field aliases you can use inside square brackets in @SQL filters, e.g.:
#   @SQL=[Subject] LIKE '%report%' AND [ReceivedTime] >= '2025-10-01 00:00'
# Notes:
# - Available aliases can vary by store/provider. If an alias is not recognized, use a DASL name instead
#   (e.g., "http://schemas.microsoft.com/mapi/proptag/0x0037001F" for Subject) or a URN schema such as
#   "urn:schemas:httpmail:subject".
# - Wrap aliases in [brackets]  when calling Items.Restrict.
# - For dates, use ISO-like strings or properly constructed COM dates.
OUTLOOK_ATSQL_ALIASES: tuple[str, ...] = (
    # Mail/general
    'Subject', 'Body', 'Categories', 'MessageClass', 'Size', 'Importance', 'Sensitivity', 'UnRead', 'HasAttachment',
    'EntryID', 'ConversationTopic',
    # Sender/recipients
    'SenderName', 'SenderEmailAddress', 'SenderEmailType', 'To', 'CC', 'BCC',
    # Time fields
    'ReceivedTime', 'SentOn', 'CreationTime', 'LastModificationTime',
    # Calendar/task-related (usable when applicable)
    'Start', 'End', 'Duration', 'Location', 'Organizer', 'MeetingStatus', 'FlagStatus', 'FlagRequest', 'FlagDueBy',
)


def get_outlook_sql_aliases() -> Iterable[str]:
    """Return a tuple of commonly recognized Outlook @SQL field aliases.

    Outlook's @SQL provider recognizes a set of field aliases that can be referenced with [Alias]
    inside an @SQL=... restriction string (Items.Restrict). The exact set may vary depending on the
    store/provider and Outlook version. If a field is not recognized in your environment, switch to
    using a DASL property name (e.g., an http://schemas.microsoft.com/mapi/proptag/... URL) or a
    URN such as urn:schemas:httpmail:... for headers.

    Examples:
    - @SQL=[Subject] = 'Weekly Report'
    - @SQL=[UnRead] = True AND [HasAttachment] = True
    - @SQL=[ReceivedTime] >= '2025-10-01 00:00' AND [SenderEmailAddress] LIKE '%@contoso.com'

    Returns:
        Iterable[str]: An iterable of alias strings that are commonly supported.
    """
    return OUTLOOK_ATSQL_ALIASES
