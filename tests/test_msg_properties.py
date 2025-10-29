import unittest

from PyEmailerAJM.backend.enums import EmailMsgImportanceLevel
from PyEmailerAJM.msg.msg import Msg


class DummyExchangeUser:
    def __init__(self, primary):
        self.PrimarySmtpAddress = primary


class DummySender:
    def __init__(self, primary):
        self._primary = primary

    def GetExchangeUser(self):
        return DummyExchangeUser(self._primary)


class DummyEmailItem:
    def __init__(self):
        # Defaults resembling an Outlook item
        self.SenderEmailType = 'SMTP'
        self.SenderEmailAddress = 'sender@example.com'
        self.Sender = DummySender('ex_sender@example.com')
        self.To = 'to@example.com'
        self.CC = 'cc@example.com'
        self.Subject = 'Subject'
        self.ReceivedTime = None
        self.HTMLBody = '<p>body</p>'
        self.Attachments = []
        self.Importance = EmailMsgImportanceLevel.NORMAL.value


class TestMsgBasicProperties(unittest.TestCase):
    def setUp(self):
        self.item = DummyEmailItem()
        self.msg = Msg(self.item)

    def test_sender_email_type_default_when_missing(self):
        # Remove the attribute to trigger default path
        if hasattr(self.item, 'SenderEmailType'):
            delattr(self.item, 'SenderEmailType')
        self.assertEqual(self.msg.sender_email_type, 'SMTP')

    def test_sender_when_exchange_type(self):
        self.item.SenderEmailType = 'EX'
        self.assertEqual(self.msg.sender, 'ex_sender@example.com')

    def test_sender_when_smtp_type(self):
        self.item.SenderEmailType = 'SMTP'
        self.assertEqual(self.msg.sender, 'sender@example.com')

    def test_importance_setter_accepts_enum(self):
        self.msg.importance = EmailMsgImportanceLevel.HIGH
        self.assertEqual(self.item.Importance, EmailMsgImportanceLevel.HIGH.value)

    def test_importance_setter_accepts_name(self):
        self.msg.importance = 'LOW'
        self.assertEqual(self.item.Importance, EmailMsgImportanceLevel.LOW.value)

    def test_importance_setter_accepts_int(self):
        self.msg.importance = 1
        self.assertEqual(self.item.Importance, 1)

    def test_importance_setter_rejects_invalid(self):
        with self.assertRaises(TypeError):
            self.msg.importance = 'INVALID'


if __name__ == '__main__':
    unittest.main()
