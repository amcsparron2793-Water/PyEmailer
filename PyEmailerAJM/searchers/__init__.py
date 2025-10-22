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


from PyEmailerAJM.searchers.searchers import BaseSearcher, SubjectSearcher, AttributeSearcher
from PyEmailerAJM.searchers.factory import SearcherFactory


__all__ = ['BaseSearcher', 'AttributeSearcher',
           'SubjectSearcher', 'SearcherFactory',
           'OUTLOOK_ATSQL_ALIASES']