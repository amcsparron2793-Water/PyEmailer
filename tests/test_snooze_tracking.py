import json
import logging
import unittest
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

from PyEmailerAJM.backend import SnoozeTracking


class TestSnoozeTracking(unittest.TestCase):

    def setUp(self):
        self.file_path = Path("/tmp/test.json")
        self.logger = logging.getLogger('test_logger')
        self.subject = "Test Email Subject"
        self.snooze_time = datetime.now() + timedelta(days=2)
        self.email_entries = {
            self.subject: self.snooze_time.isoformat()
        }

        self.snooze_tracking = SnoozeTracking(self.file_path, logger=self.logger)

    @patch('json.load')
    @patch('builtins.open')
    def test_json_loaded(self, mock_open, mock_json_load):
        mock_json_load.return_value = self.email_entries
        loaded_json = self.snooze_tracking.json_loaded
        mock_open.assert_called_once_with(self.file_path, 'r')
        self.assertEqual(loaded_json, self.email_entries, 'Should load JSON data from file')

    @patch('json.load')
    @patch('builtins.open')
    def test_write_entry(self, mock_open, mock_json_load):
        mock_json_load.return_value = {}
        new_snooze_time = datetime.now() + timedelta(days=3)
        self.snooze_tracking.write_entry(self.subject, new_snooze_time)
        self.assertEqual(self.snooze_tracking.json_loaded[self.subject], new_snooze_time,
                         'Should write entry to json_loaded')

    def test_convert_datetime(self):
        non_dt_val = "non_datetime_value"
        dt_val = datetime.now()
        self.assertEqual(self.snooze_tracking._convert_datetime(non_dt_val), non_dt_val,
                         'Non datetime value should remain unchanged')
        self.assertEqual(self.snooze_tracking._convert_datetime(dt_val), dt_val.isoformat(),
                         'Datetime value should be iso formatted')

    @patch('json.dump')
    @patch('builtins.open')
    def test_save_json(self, mock_open, mock_json_dump):
        self.snooze_tracking._json_loaded = self.email_entries
        self.snooze_tracking.save_json()
        self.logger.info.assert_called_with(f"json saved to {self.file_path}")
        mock_open.assert_called_once_with(self.file_path, 'w')
        mock_json_dump.assert_called_once()

    def test_read_entry(self):
        self.snooze_tracking._json_loaded = self.email_entries
        output_snooze_time = self.snooze_tracking.read_entry(self.subject)
        self.assertEqual(output_snooze_time, self.snooze_time, 'Should correctly read snooze time from json_loaded')

    def test_snooze_msgs(self):
        mock_msg_1 = Mock()
        mock_msg_1.subject = "msg_1"
        mock_msg_1.msg_snoozed = False
        mock_msg_1.msg_snoozed_time = datetime.now() + timedelta(days=3)

        mock_msg_2 = Mock()
        mock_msg_2.subject = "msg_2"
        mock_msg_2.msg_snoozed = True
        mock_msg_2.msg_snoozed_time = datetime.now() + timedelta(days=1)

        msg_list = [mock_msg_1, mock_msg_2]
        output_msg_list = self.snooze_tracking.snooze_msgs(msg_list)
        self.assertEqual(output_msg_list, msg_list, 'Should return the same list')
        self.assertTrue(output_msg_list[0].msg_snoozed, 'Non-snoozed message should be marked as snoozed')


if __name__ == "__main__":
    unittest.main()
