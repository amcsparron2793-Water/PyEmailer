import unittest
from unittest.mock import patch, MagicMock
import logging

from PyEmailerAJM.continuous_monitor.backend import ContinuousMonitorBase


class DummyMonitor(ContinuousMonitorBase):
    def _postprocess_alert(self, alert_level=None, **kwargs):
        # Mark that postprocess was called
        self.postprocess_called = True


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

        # Provide a dummy logger class callable that returns a real Logger-like mock
        class DummyLoggerClass:
            def __call__(self):
                mock_logger = MagicMock(spec=logging.Logger)
                # emulate hasHandlers/handlers used in code paths
                mock_logger.hasHandlers.return_value = False
                mock_logger.handlers = []
                return mock_logger

        self.DummyLoggerClass = DummyLoggerClass

    def tearDown(self) -> None:
        self._post_handler_patcher.stop()
        self._init_email_patch.stop()

    def test_dev_mode_logs_and_disables_email_handler(self):
        monitor = DummyMonitor(display_window=False, send_emails=False, dev_mode=True, logger=self.DummyLoggerClass())

        # Expect dev mode warnings
        logger = monitor.logger
        calls = [c.args[0] for c in logger.warning.call_args_list]
        self.assertTrue(any('DEV MODE ACTIVATED!' in msg for msg in calls))
        self.assertTrue(any('email handler disabled for dev mode' in msg for msg in calls))

    def test_non_alert_subclass_does_not_init_email_handler(self):
        monitor = DummyMonitor(display_window=False, send_emails=False, dev_mode=False, logger=self.DummyLoggerClass())

        # Should warn that email handler not initialized for non-ContinuousMonitorAlertSend subclass
        logger = monitor.logger
        calls = [c.args[0] for c in logger.warning.call_args_list]
        self.assertTrue(any('not initialized because this is not a ContinuousMonitorAlertSend subclass' in msg
                            for msg in calls))

    def test_print_and_postprocess_calls_postprocess_when_not_dev(self):
        monitor = DummyMonitor(display_window=False, send_emails=False, dev_mode=False, logger=self.DummyLoggerClass())
        monitor.postprocess_called = False
        monitor._print_and_postprocess(alert_level='INFO')
        self.assertTrue(monitor.postprocess_called)

    def test_print_and_postprocess_skips_postprocess_in_dev(self):
        monitor = DummyMonitor(display_window=False, send_emails=False, dev_mode=True, logger=self.DummyLoggerClass())
        monitor.postprocess_called = False
        monitor._print_and_postprocess(alert_level='INFO')
        self.assertFalse(monitor.postprocess_called)


if __name__ == '__main__':
    unittest.main()
