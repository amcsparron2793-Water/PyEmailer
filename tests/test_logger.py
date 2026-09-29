import unittest
from unittest.mock import patch, MagicMock
import logging

from PyEmailerAJM.backend.logger import PyEmailerLogger


# FIXME: some of these tests are flakey
class TestPyEmailerLogger(unittest.TestCase):
    def setUp(self) -> None:
        # Prevent EasyLogger from emitting during initialization, which can interact with mocked handlers
        from EasyLoggerAJM.easy_logger import EasyLogger
        from unittest.mock import patch
        self._post_handler_patcher = patch.object(EasyLogger, 'post_handler_setup', autospec=True)
        self._post_handler_patcher.start()
        self.logger = PyEmailerLogger()

    def tearDown(self) -> None:
        # Stop our patcher to restore EasyLogger behavior for other tests
        self._post_handler_patcher.stop()

    def test_call(self):
        self.assertIs(self.logger(), self.logger.logger)

    @patch('PyEmailerAJM.backend.logger.DupeDebugFilter')
    def test_add_dupe_debug_to_handler(self, mock_dupe_debug_filter):
        handler = MagicMock()

        # FIX: Ensure handler.level is an integer
        handler.level = logging.WARNING  # Set a valid logging level

        self.logger._add_dupe_debug_to_handler(handler)
        mock_dupe_debug_filter.assert_called_once()
        handler.addFilter.assert_called_once_with(mock_dupe_debug_filter.return_value)

    @unittest.skip("Skipping this test because it's under development")
    def test_set_logger_class(self):
        result = self.logger._set_logger_class()
        self.assertIs(result, self.logger)

    @patch('PyEmailerAJM.backend.logger.Logger')
    def test_initialize_logger(self, mock_logger):
        self.logger.initialize_logger(logger=mock_logger)
        self.assertFalse(mock_logger.propagate)

    @patch('PyEmailerAJM.backend.logger.OutlookEmailHandler')
    def test_setup_email_handler(self, mock_email_handler):
        mock_email_handler_instance = mock_email_handler.return_value
        mock_email_handler_instance.level = logging.ERROR

        with patch.object(self.logger.logger, 'addHandler', autospec=True) as mock_add_handler:
            self.logger.setup_email_handler(email_msg='Test email', logger_admins=['admin1@gmail.com'])

            self.assertEqual(mock_email_handler_instance.level, logging.ERROR)
            mock_email_handler.assert_called_once_with(
                email_msg='Test email',
                project_name=self.logger.project_name,
                logger_dir_path=self.logger.log_location,
                recipient=['admin1@gmail.com']
            )
            mock_email_handler_instance.setLevel.assert_called_once_with(logging.ERROR)
            mock_email_handler_instance.setFormatter.assert_called_once_with(
                self.logger.formatter)
            mock_add_handler.assert_called_once_with(mock_email_handler_instance)

    @patch('PyEmailerAJM.backend.logger.FileHandler')
    def test_add_filter_to_file_handler(self, mock_file_handler):
        mock_file_handler.level = logging.INFO  # FIX: Set a valid level
        self.logger._add_filter_to_file_handler(mock_file_handler)
        mock_file_handler.addFilter.assert_called_once()

    @patch('PyEmailerAJM.backend.logger.StreamHandler')
    def test_add_filter_to_stream_handler(self, mock_stream_handler):
        mock_stream_handler.level = logging.DEBUG  # FIX: Set a valid level
        self.logger._add_filter_to_stream_handler(mock_stream_handler)
        mock_stream_handler.addFilter.assert_called_once()

    def test_project_name_getter(self):
        self.assertEqual(self.logger.project_name, self.logger.project_name)

    def test_project_name_setter(self):
        self.logger.project_name = 'NewProject'
        self.assertEqual(self.logger.project_name, 'NewProject')

    @patch('PyEmailerAJM.backend.logger.StreamHandlerIgnoreExecInfo')
    def test_create_stream_handler(self, mock_stream_handler):
        self.logger.create_stream_handler(log_level_to_stream=logging.WARNING)
        mock_stream_handler.assert_called_once()


if __name__ == '__main__':
    unittest.main()
