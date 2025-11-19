import unittest
from unittest.mock import patch, MagicMock
import logging
from pathlib import Path

from PyEmailerAJM.continuous_monitor.backend import ContinuousMonitorBase


class DummyMonitor(ContinuousMonitorBase):
    def _postprocess_alert(self, alert_level=None, **kwargs):
        # Mark that postprocess was called
        self.postprocess_called = True


# Make DummyMonitor look like ContinuousMonitorAlertSend for the type check
class ContinuousMonitorAlertSend(ContinuousMonitorBase):
    """Mock subclass that passes the type check in email_handler_init"""

    def _postprocess_alert(self, alert_level=None, **kwargs):
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


# Dummy helper classes for initialize_helper_classes behavior checks
class DummyColorizer:
    def __init__(self, logger=None, **kwargs):
        self.logger = logger
        self.kwargs = kwargs


class DummySnoozeTracker:
    def __init__(self, file_path: Path, logger=None, **kwargs):
        self.file_path = file_path
        self.logger = logger
        self.kwargs = kwargs
        # default internal state for snooze json
        self.json_loaded = []


class DummySleepTimer:
    def __init__(self, sleep_time_seconds=None, logger=None, **kwargs):
        self.sleep_time_seconds = sleep_time_seconds
        self.logger = logger
        self.kwargs = kwargs


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

    def test_skips_email_handler_when_not_alert_send_subclass(self):
        monitor = DummyMonitor(display_window=False, send_emails=False, dev_mode=False,
                               logger=self.LoggerFactoryNoEmail)

        # Should warn that email handler not initialized because not subclass
        logger = monitor.logger
        warning_calls = [c.args[0] for c in logger.warning.call_args_list]
        self.assertTrue(
            any('not initialized because this is not a ContinuousMonitorAlertSend' in msg for msg in warning_calls))

    def test_print_and_postprocess_calls_postprocess_when_not_dev(self):
        monitor = DummyMonitor(display_window=False, send_emails=False, dev_mode=False,
                               logger=self.LoggerFactoryNoEmail)
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
            # Use ContinuousMonitorAlertSend instead of DummyMonitor to pass the type check
            monitor = ContinuousMonitorAlertSend(display_window=False, send_emails=False, dev_mode=False,
                                                 logger=self.LoggerFactoryWithEmail)
        # Logger factory should have been used to setup email handler with original email
        self.assertIsNotNone(self.LoggerFactoryWithEmail._last_kwargs)
        self.assertIn('email_msg', self.LoggerFactoryWithEmail._last_kwargs)
        # After init, email should be replaced with NEW_EMAIL
        self.assertEqual(monitor.email, 'NEW_EMAIL')

    def test_email_handler_init_handles_attribute_error(self):
        # When logger_class lacks setup_email_handler, should be caught and not raise
        monitor = ContinuousMonitorAlertSend(display_window=False, send_emails=False, dev_mode=False,
                                             logger=self.LoggerFactoryWithEmail)
        # Use a dummy object without setup_email_handler to trigger AttributeError
        monitor.email_handler_init(logger_class=object())
        # Ensure an error was logged
        error_calls = [c.args[0] for c in monitor.logger.error.call_args_list]
        self.assertTrue(any('email handler not initialized because' in msg for msg in error_calls))

    def test_is_continuous_monitor_alert_send_subclass(self):
        a = DummyMonitor(display_window=False, send_emails=False, dev_mode=False, logger=self.LoggerFactoryNoEmail)
        b = ContinuousMonitorAlertSend(display_window=False, send_emails=False, dev_mode=False,
                                       logger=self.LoggerFactoryNoEmail)
        self.assertFalse(a._is_continuous_monitor_alert_send_subclass())
        self.assertTrue(b._is_continuous_monitor_alert_send_subclass())

    def test_should_skip_email_handler_init_paths(self):
        # dev mode skips
        m1 = ContinuousMonitorAlertSend(display_window=False, send_emails=False, dev_mode=True,
                                        logger=self.LoggerFactoryNoEmail)
        self.assertTrue(m1._should_skip_email_handler_init())
        # not subclass skips
        m2 = DummyMonitor(display_window=False, send_emails=False, dev_mode=False, logger=self.LoggerFactoryNoEmail)
        self.assertTrue(m2._should_skip_email_handler_init())
        # valid subclass and not dev mode does not skip
        m3 = ContinuousMonitorAlertSend(display_window=False, send_emails=False, dev_mode=False,
                                        logger=self.LoggerFactoryNoEmail)
        self.assertFalse(m3._should_skip_email_handler_init())

    def test_normalize_logger_with_factory_and_instance(self):
        # Using factory returns a logger instance
        m = DummyMonitor(display_window=False, send_emails=False, dev_mode=False, logger=self.LoggerFactoryNoEmail)
        l_from_factory = m._normalize_logger(logger=self.LoggerFactoryNoEmail)
        self.assertTrue(hasattr(l_from_factory, 'info'))
        # Using instance returns the same instance
        logger_instance = MagicMock(spec=logging.Logger)
        l_from_instance = m._normalize_logger(logger=logger_instance)
        self.assertIs(l_from_instance, logger_instance)
        # Not providing logger uses self.logger
        l_default = m._normalize_logger()
        self.assertIs(l_default, m.logger)

    def test_initialize_helper_classes_and_num_snoozed_msgs(self):
        m = DummyMonitor(display_window=False, send_emails=False, dev_mode=False, logger=self.LoggerFactoryNoEmail)
        colorizer, snoozer, sleeper = m.initialize_helper_classes(
            colorizer=DummyColorizer,
            snooze_tracker=DummySnoozeTracker,
            sleep_timer=DummySleepTimer,
            file_name='my_snooze.json',
            sleep_time_seconds=42,
            extra_opt=123
        )
        # helper types
        self.assertIsInstance(colorizer, DummyColorizer)
        self.assertIsInstance(snoozer, DummySnoozeTracker)
        self.assertIsInstance(sleeper, DummySleepTimer)
        # logger propagated
        self.assertIs(colorizer.logger, m.logger)
        self.assertIs(snoozer.logger, m.logger)
        self.assertIs(sleeper.logger, m.logger)
        # file path and sleep time propagated and processed
        self.assertTrue(str(snoozer.file_path).endswith('my_snooze.json'))
        self.assertEqual(sleeper.sleep_time_seconds, 42)
        # extra options should pass to colorizer and snoozer and sleeper
        self.assertEqual(colorizer.kwargs.get('extra_opt'), 123)
        self.assertEqual(snoozer.kwargs.get('extra_opt'), 123)
        self.assertEqual(sleeper.kwargs.get('extra_opt'), 123)
        # Verify num_snoozed_msgs reflects json_loaded length
        m.snooze_tracker = snoozer
        snoozer.json_loaded = [1, 2, 3]
        self.assertEqual(m.num_snoozed_msgs, 3)
        # When no json_loaded or not sized, expect 0
        snoozer.json_loaded = None
        self.assertEqual(m.num_snoozed_msgs, 0)

    def test_check_for_class_attrs(self):
        class GoodSub(ContinuousMonitorBase):
            ADMIN_EMAIL = ['a@example.com']

            def _postprocess_alert(self, alert_level=None, **kwargs):
                pass

        class BadSub(ContinuousMonitorBase):
            ADMIN_EMAIL = []

            def _postprocess_alert(self, alert_level=None, **kwargs):
                pass

        # Good should not raise
        GoodSub.check_for_class_attrs(['ADMIN_EMAIL'])
        # Bad should raise
        with self.assertRaises(ValueError):
            BadSub.check_for_class_attrs(['ADMIN_EMAIL'])


if __name__ == '__main__':
    unittest.main()
