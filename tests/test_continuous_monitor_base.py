import unittest
from unittest.mock import patch, MagicMock
import logging

from PyEmailerAJM.continuous_monitor.backend import ContinuousMonitorBase


class DummyMonitor(ContinuousMonitorBase):
    def _postprocess_alert(self, alert_level=None, **kwargs):
        # Mark that postprocess was called
        self.postprocess_called = True


class DummyLoggerFactory:
    """Callable logger factory with optional setup_email_handler capability"""
    def __init__(self, with_email_handler=False):
        self.with_email_handler = with_email_handler
        self._last_kwargs = None

    def __call__(self):
        # Return a real Logger-like mock
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.hasHandlers.return_value = False
        mock_logger.handlers = []
        return mock_logger

    def setup_email_handler(self, **kwargs):
        # record kwargs for assertion
        self._last_kwargs = kwargs


class TestContinuousMonitorBase(unittest.TestCase):
    def setUp(self) -> None:
        # Avoid actual COM/Outlook initialization
        self._init_email_patch = patch(
            'PyEmailerAJM.py_emailer_ajm.EmailerInitializer.initialize_email_item_app_and_namespace',
            return_value=(None, None, MagicMock())
        )
        self._init_email_patch.start()

        # Prevent EasyLogger from emitting during initialization
        from EasyLoggerAJM.easy_logger import EasyLogger
        self._post_handler_patcher = patch.object(EasyLogger, 'post_handler_setup', autospec=True)
        self._post_handler_patcher.start()

        # Provide logger factories used by tests
        self.LoggerFactoryNoEmail = DummyLoggerFactory(with_email_handler=False)
        self.LoggerFactoryWithEmail = DummyLoggerFactory(with_email_handler=True)

    def tearDown(self) -> None:
        self._post_handler_patcher.stop()
        self._init_email_patch.stop()

    def test_dev_mode_logs_and_disables_email_handler(self):
        monitor = DummyMonitor(display_window=False, send_emails=False, dev_mode=True, logger=self.LoggerFactoryNoEmail)

        # Expect dev mode warnings
        logger = monitor.logger
        calls = [c.args[0] for c in logger.warning.call_args_list]
        self.assertTrue(any('DEV MODE ACTIVATED!' in msg for msg in calls))
        self.assertTrue(any('email handler disabled for dev mode' in msg for msg in calls))

    def test_skips_email_handler_when_logger_factory_has_no_setup(self):
        monitor = DummyMonitor(display_window=False, send_emails=False, dev_mode=False, logger=self.LoggerFactoryNoEmail)

        # Should debug that email handler not initialized due to lack of capability
        logger = monitor.logger
        debug_calls = [c.args[0] for c in logger.debug.call_args_list]
        self.assertTrue(any('has no setup_email_handler' in msg for msg in debug_calls))

    def test_print_and_postprocess_calls_postprocess_when_not_dev(self):
        monitor = DummyMonitor(display_window=False, send_emails=False, dev_mode=False, logger=self.LoggerFactoryNoEmail)
        monitor.postprocess_called = False
        monitor._print_and_postprocess(alert_level='INFO')
        self.assertTrue(monitor.postprocess_called)

    def test_print_and_postprocess_skips_postprocess_in_dev(self):
        monitor = DummyMonitor(display_window=False, send_emails=False, dev_mode=True, logger=self.LoggerFactoryNoEmail)
        monitor.postprocess_called = False
        monitor._print_and_postprocess(alert_level='INFO')
        self.assertFalse(monitor.postprocess_called)

    def test_initializes_email_handler_when_factory_supports_it(self):
        # Patch fresh email creation to a sentinel value and verify it gets set
        with patch('PyEmailerAJM.py_emailer_ajm.EmailerInitializer.initialize_new_email', return_value='NEW_EMAIL'):
            monitor = DummyMonitor(display_window=False, send_emails=False, dev_mode=False,
                                   logger=self.LoggerFactoryWithEmail)
        # Logger factory should have been used to setup email handler with original email
        self.assertIsNotNone(self.LoggerFactoryWithEmail._last_kwargs)
        self.assertIn('email_msg', self.LoggerFactoryWithEmail._last_kwargs)
        # After init, email should be replaced with NEW_EMAIL
        self.assertEqual(monitor.email, 'NEW_EMAIL')


if __name__ == '__main__':
    unittest.main()
