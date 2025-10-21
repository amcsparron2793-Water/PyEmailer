from typing import Iterable

from .searchers import SubjectSearcher


# TODO: flesh me out
class SearcherFactory:
    SEARCHER_CLASSES = [SubjectSearcher,]

    @staticmethod
    def get_searcher(search_type):
        if search_type == 'subject':
            return SubjectSearcher()
        else:
            raise ValueError('Invalid search type')


# TODO: add these as options
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
