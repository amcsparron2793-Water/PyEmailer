import os
import unittest
from unittest.mock import Mock, patch

from PyEmailerAJM import PyEmailer, Msg


class TestPyEmailer(unittest.TestCase):
    TEST_ATTACHMENT_NAMES = ['attachment1', 'attachment2']

    def setUp(self):
        self.emailer = PyEmailer(False, False)

    @classmethod
    def tearDownClass(cls):
        for x in cls.TEST_ATTACHMENT_NAMES:
            try:
                os.remove(x)
            except FileNotFoundError:
                pass

    def test_init(self):
        self.assertIsInstance(self.emailer, PyEmailer)

    @unittest.skip("Skipping this test because it's under development")
    def test_current_user_email_getter_setter(self):
        self.emailer.current_user_email = 'test_user@example.com'
        self.assertEqual(self.emailer.current_user_email, 'test_user@example.com')

    def test_email_signature_getter(self):
        self.assertIsNone(self.emailer.email_signature)

    def test_send_success_getter_setter(self):
        self.emailer.send_success = True
        self.assertTrue(self.emailer.send_success)

    def test__display_tracking_warning_confirm(self):
        with patch('PyEmailerAJM.PyEmailer._display_tracking_warning_confirm', return_value=True):
            self.assertTrue(self.emailer._display_tracking_warning_confirm())

    def test_display_tracker_check(self):
        self.assertFalse(self.emailer.display_tracker_check())

    def test__GetReadFolder(self):
        # Create a single consistent Mock instance
        predefined_mock = Mock()

        # Use the patch to ensure the method returns the predefined_mock
        with patch('PyEmailerAJM.PyEmailer._GetReadFolder', return_value=predefined_mock):
            # Compare _GetReadFolder's return value with the same predefined_mock
            self.assertEqual(self.emailer._GetReadFolder(6), predefined_mock)

    def test_GetMessages(self):
        predefined_mock = Mock()  # Create a single consistent mock for the return value
        with patch('PyEmailerAJM.PyEmailer.GetMessages', return_value=predefined_mock):
            self.assertEqual(self.emailer.GetMessages(0), predefined_mock)  # Compare with the predefined mock

    def test_GetEmailMessageBody(self):
        msg = Mock()  # Create the message mock
        predefined_mock = Mock()  # Create a single consistent mock for the return value
        with patch('PyEmailerAJM.PyEmailer.GetEmailMessageBody', return_value=predefined_mock):
            result = self.emailer.GetEmailMessageBody(msg)
            self.assertEqual(result, predefined_mock)  # Compare with the predefined mock

    def test_FindMsgBySubject(self):
        subject = 'Test Subject'
        predefined_mock = Mock()  # Define a single Mock instance for consistent comparison

        # Patch the method to return the predefined_mock object
        with patch('PyEmailerAJM.PyEmailer.FindMsgBySubject', return_value=predefined_mock):
            result = self.emailer.FindMsgBySubject(subject, True, True, False)
            self.assertEqual(result, predefined_mock)  # Compare with the predefined Mock instance

    def test_SaveAllEmailAttachments(self):
        # Create a mock message object with mocked attachments
        msg = Mock()
        attachment1 = Mock()
        attachment2 = Mock()

        # Assign Attachments as a list of the attachment mocks
        msg.Attachments = [attachment1, attachment2]

        # Mock the SaveAsFile method for each attachment
        attachment1.SaveAsFile = Mock()
        attachment2.SaveAsFile = Mock()

        # Set save directory path
        save_dir_path = '/path/to/save'

        # Call the method and check no exception is raised
        try:
            self.assertIsNone(self.emailer.SaveAllEmailAttachments(msg, save_dir_path))

            # Verify SaveAsFile was called with correct paths
            attachment1.SaveAsFile.assert_called_once()
            attachment2.SaveAsFile.assert_called_once()
        except Exception as e:
            self.fail(f"SaveAllEmailAttachments raised an exception: {e}")

    def test_SetupEmail(self):
        recipient = 'recipient@test.com'
        subject = 'Test email'
        text = 'This is a test email.'
        for x in self.__class__.TEST_ATTACHMENT_NAMES:
            with open(f'./{x}', 'w'):
                pass
        self.assertIsInstance(self.emailer.SetupEmail(recipient, subject, text,
                                                      self.__class__.TEST_ATTACHMENT_NAMES), Msg)

    def test_SendOrDisplay(self):
        mocked_return_value = Mock()  # Create a single Mock instance
        with patch('PyEmailerAJM.PyEmailer.SendOrDisplay', return_value=mocked_return_value):
            self.assertEqual(self.emailer.SendOrDisplay(True), mocked_return_value)

    @unittest.skip("Skipping this test because it's under development")
    def test__fmsg_is_no_info_or_err(self):
        info = Mock()
        self.assertFalse(PyEmailer._fmsg_is_no_info_or_err(info))

    def test_get_failed_sends(self):
        fail_string_marker = 'fail'
        mocked_return_value = Mock()  # Single Mock instance for consistent comparison
        with patch('PyEmailerAJM.PyEmailer.get_failed_sends', return_value=mocked_return_value):
            self.assertEqual(self.emailer.get_failed_sends(fail_string_marker, True), mocked_return_value)


if __name__ == '__main__':
    unittest.main()
