import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path
from PyEmailerAJM.continuous_monitor.continuous_monitor_alert_send import ContinuousMonitorAlertSend, NonEmailTriggerCMAS
from PyEmailerAJM.backend import EmailMsgImportanceLevel, AlertTypes
from pythoncom import com_error

class TestContinuousMonitorAlertSend(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_colorizer = MagicMock()
        self.mock_snooze_tracker = MagicMock()
        self.mock_sleep_timer = MagicMock()
        
        # Patching necessary methods in the base classes to avoid side effects
        self.patcher_init_helpers = patch('PyEmailerAJM.continuous_monitor.backend.continuous_monitor_base.CMASHelperClasses.initialize_helper_classes')
        self.mock_init_helpers = self.patcher_init_helpers.start()
        # It expects 3 values: colorizer, snooze_tracker, sleep_timer
        self.mock_init_helpers.return_value = (self.mock_colorizer, self.mock_snooze_tracker, self.mock_sleep_timer)
        
        # We need to block EmailerInitializer.__init__ from running its real code
        # but we need to ensure self.logger is set because PyEmailer.__init__ uses it.
        def mock_init(instance, *args, **kwargs):
            instance.logger = self.mock_logger
            instance.email_app_name = 'outlook.application'
            instance.namespace_name = 'MAPI'
            instance.display_window = args[0] if args else kwargs.get('display_window', False)
            instance.send_emails = args[1] if len(args) > 1 else kwargs.get('send_emails', False)
            instance.auto_send = kwargs.get('auto_send', False)

        self.patcher_emailer_init = patch('PyEmailerAJM.py_emailer_ajm.EmailerInitializer.__init__', side_effect=mock_init, autospec=True)
        self.patcher_emailer_init.start()
        
        # Mocking SearcherFactory to avoid real initialization
        self.patcher_searcher_factory = patch('PyEmailerAJM.py_emailer_ajm.SearcherFactory')
        self.mock_searcher_factory = self.patcher_searcher_factory.start()
        self.mock_searcher = MagicMock()
        self.mock_searcher_factory.return_value.get_searcher.return_value = self.mock_searcher

        # We need to ensure ContinuousMonitorBase.__init__ doesn't fail
        # It calls initialize_helper_classes, email_handler_init, and log_dev_mode_warnings
        self.patcher_email_handler_init = patch('PyEmailerAJM.continuous_monitor.backend.continuous_monitor_base.ContinuousMonitorBase.email_handler_init')
        self.patcher_email_handler_init.start()
        
        # Mocking signature
        self.patcher_signature = patch('PyEmailerAJM.py_emailer_ajm.PyEmailer.email_signature', new_callable=PropertyMock)
        self.mock_signature = self.patcher_signature.start()
        self.mock_signature.return_value = "Andrew Full\nDeveloper"

        # Mock initialize_new_email and SetupEmail for refresh_messages
        self.patcher_init_new_email = patch('PyEmailerAJM.py_emailer_ajm.EmailerInitializer.initialize_new_email')
        self.mock_init_new_email = self.patcher_init_new_email.start()
        
        self.patcher_super_setup_email = patch('PyEmailerAJM.py_emailer_ajm.PyEmailer.SetupEmail')
        self.mock_super_setup_email = self.patcher_super_setup_email.start()

        self.patcher_super_refresh = patch('PyEmailerAJM.continuous_monitor.backend.continuous_monitor_base.ContinuousMonitorBase.refresh_messages')
        self.patcher_super_refresh.start()

        # Mocking GetMessages for response_body
        self.patcher_get_messages = patch('PyEmailerAJM.continuous_monitor.continuous_monitor_alert_send.ContinuousMonitorAlertSend.GetMessages')
        self.mock_get_messages = self.patcher_get_messages.start()
        self.mock_get_messages.return_value = []

        # Concrete class for testing
        class MockCMAS(ContinuousMonitorAlertSend):
            ADMIN_EMAIL = ['test@example.com']
            ADMIN_EMAIL_LOGGER = ['test@example.com']

        self.MockCMAS = MockCMAS

    def tearDown(self):
        patch.stopall()

    def test_init_checks_attrs_when_not_dev_mode(self):
        # We need to ensure that the call to self.__class__.check_for_class_attrs
        # is captured. If we patch the base class version, and it's called on the subclass,
        # it should still be captured if patched correctly.
        with patch('PyEmailerAJM.continuous_monitor.backend.continuous_monitor_base.ContinuousMonitorBase.check_for_class_attrs') as mock_check:
            # We must be careful because ContinuousMonitorAlertSend.__init__ 
            # uses "if type(self) is ContinuousMonitorAlertSend:"
            # So if we use MockCMAS, it WON'T call it.
            instance = ContinuousMonitorAlertSend(display_window=False, send_emails=True, dev_mode=False)
            mock_check.assert_called_with(instance.ATTRS_TO_CHECK)

    def test_init_skips_attrs_in_dev_mode(self):
        with patch('PyEmailerAJM.continuous_monitor.backend.continuous_monitor_base.ContinuousMonitorBase.check_for_class_attrs') as mock_check:
            instance = self.MockCMAS(display_window=False, send_emails=True, dev_mode=True)
            mock_check.assert_not_called()
            self.mock_logger.warning.assert_called()

    def test_set_args_for_endless_watch(self):
        instance = self.MockCMAS(display_window=True, send_emails=False, dev_mode=False)
        instance._set_args_for_endless_watch()
        self.assertTrue(instance.send_emails)
        self.assertTrue(instance.auto_send)
        self.assertFalse(instance.display_window)

    def test_SetupEmail_defaults(self):
        instance = self.MockCMAS(display_window=False, send_emails=True, dev_mode=True)
        # Mock response_body to avoid complex formatting logic here
        with patch.object(self.MockCMAS, 'response_body', new_callable=PropertyMock) as mock_rb:
            mock_rb.return_value = "Test Body"
            instance.SetupEmail()
            self.mock_super_setup_email.assert_called_with(
                recipient='test@example.com',
                subject=instance.DEFAULT_SUBJECT,
                text="Test Body",
                attachments=None
            )

    def test_SetupEmail_multiple_recipients(self):
        self.MockCMAS.ADMIN_EMAIL = ['a@example.com', 'b@example.com']
        instance = self.MockCMAS(display_window=False, send_emails=True, dev_mode=True)
        with patch.object(self.MockCMAS, 'response_body', new_callable=PropertyMock) as mock_rb:
            mock_rb.return_value = "Test Body"
            instance.SetupEmail()
            self.mock_super_setup_email.assert_called_with(
                recipient='a@example.com ;b@example.com',
                subject=instance.DEFAULT_SUBJECT,
                text="Test Body",
                attachments=None
            )

    def test_get_response_body_alert_level_no_colorizer(self):
        instance = self.MockCMAS(display_window=False, send_emails=True, dev_mode=True)
        from PyEmailerAJM.continuous_monitor.continuous_monitor_alert_send import NO_COLORIZER
        with patch('PyEmailerAJM.continuous_monitor.continuous_monitor_alert_send.NO_COLORIZER', True):
            mock_msg = MagicMock()
            mock_msg.__class__.ALERT_LEVEL = AlertTypes.WARNING
            result = instance.get_response_body_alert_level(mock_msg)
            self.assertEqual(result, 'WARNING')

    def test_get_response_body_alert_level_with_colorizer(self):
        instance = self.MockCMAS(display_window=False, send_emails=True, dev_mode=True)
        with patch('PyEmailerAJM.continuous_monitor.continuous_monitor_alert_send.NO_COLORIZER', False):
            mock_msg = MagicMock()
            mock_msg.__class__.ALERT_LEVEL = AlertTypes.WARNING
            self.mock_colorizer.get_alert_color.return_value = 'yellow'
            self.mock_colorizer.colorize.return_value = '<span style="color: yellow">WARNING</span>'
            
            result = instance.get_response_body_alert_level(mock_msg)
            
            self.mock_colorizer.get_alert_color.assert_called_with(AlertTypes.WARNING)
            self.mock_colorizer.colorize.assert_called_with('WARNING', color='yellow', html_mode=True)
            self.assertEqual(result, '<span style="color: yellow">WARNING</span>')

    def test_email_signature_formatting(self):
        instance = self.MockCMAS(display_window=False, send_emails=True, dev_mode=True)
        # Original signature: "Andrew Full\nDeveloper"
        # Expected: "Andrew Full<br>Developer"
        self.assertEqual(instance.email_signature, "Andrew Full<br>Developer")

    def test_greeting_fmt_admin_email_names(self):
        self.MockCMAS.ADMIN_EMAIL = ['andrew@example.com', 'bob@example.com']
        instance = self.MockCMAS(display_window=False, send_emails=True, dev_mode=True)
        self.assertEqual(instance.greeting_fmt_admin_email_names, "andrew, bob")

    def test_response_body_formatting(self):
        self.MockCMAS.ADMIN_EMAIL = ['andrew@example.com']
        instance = self.MockCMAS(display_window=False, send_emails=True, dev_mode=True)
        
        mock_msg = MagicMock()
        mock_msg.subject = "Test Subject"
        mock_msg.__class__.ALERT_LEVEL = AlertTypes.WARNING
        self.mock_get_messages.return_value = [mock_msg]
        
        with patch.object(instance, 'get_response_body_alert_level', return_value="WARNING"):
            body = instance.response_body
            self.assertIn("Dear andrew,", body)
            self.assertIn("Test Subject - WARNING", body)
            self.assertIn("Andrew Full<br>Developer", body)

    def test_set_email_importance_default(self):
        instance = self.MockCMAS(display_window=False, send_emails=True, dev_mode=True)
        instance.email = MagicMock()
        instance._set_email_importance()
        self.assertEqual(instance.email.importance, instance.ALERT_EMAIL_IMPORTANCE)

    def test_set_email_importance_custom(self):
        instance = self.MockCMAS(display_window=False, send_emails=True, dev_mode=True)
        instance.email = MagicMock()
        instance._set_email_importance(importance_level=EmailMsgImportanceLevel.NORMAL)
        self.assertEqual(instance.email.importance, EmailMsgImportanceLevel.NORMAL)

    def test_set_email_importance_handles_error(self):
        instance = self.MockCMAS(display_window=False, send_emails=True, dev_mode=True)
        instance.email = MagicMock()
        
        # We use side_effect on the mock directly if possible, or handle PropertyMock correctly.
        # When using type(instance.email).importance = PropertyMock(side_effect=...),
        # every access (get or set) uses the side_effect.
        # In _set_email_importance:
        # 1. self.email.importance = ... (SET 1 - side_effect[0] -> raises com_error)
        # 2. self.email.importance = ... (SET 2 - side_effect[1] -> returns None)
        # 3. return self.email (No access to importance)
        # 4. In test: type(instance.email).importance.call_count (GET - side_effect[2] -> StopIteration!)
        
        mock_importance = PropertyMock(side_effect=[com_error(1, "error", None, None), None, None, None, None])
        type(instance.email).importance = mock_importance
        
        instance._set_email_importance(default_importance=EmailMsgImportanceLevel.NORMAL)
        self.mock_logger.warning.assert_called()
        self.assertGreaterEqual(mock_importance.call_count, 2)

    def test_postprocess_alert(self):
        instance = self.MockCMAS(display_window=False, send_emails=True, dev_mode=True)
        with patch.object(instance, '_set_email_importance') as mock_set_imp:
            with patch.object(instance, 'SendOrDisplay') as mock_send:
                instance._postprocess_alert(alert_level=AlertTypes.WARNING, extra_arg="test")
                mock_set_imp.assert_called_with(extra_arg="test")
                mock_send.assert_called_with(extra_arg="test")

    def test_refresh_messages(self):
        instance = self.MockCMAS(display_window=False, send_emails=True, dev_mode=True)
        with patch.object(instance, 'SetupEmail') as mock_setup:
            instance.refresh_messages()
            self.mock_init_new_email.assert_called()
            mock_setup.assert_called()

class TestNonEmailTriggerCMAS(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_colorizer = MagicMock()
        self.mock_snooze_tracker = MagicMock()
        self.mock_sleep_timer = MagicMock()

        self.patcher_init_helpers = patch('PyEmailerAJM.continuous_monitor.backend.continuous_monitor_base.CMASHelperClasses.initialize_helper_classes')
        self.mock_init_helpers = self.patcher_init_helpers.start()
        # It expects 3 values: colorizer, snooze_tracker, sleep_timer
        self.mock_init_helpers.return_value = (self.mock_colorizer, self.mock_snooze_tracker, self.mock_sleep_timer)
        
        def mock_init(instance, *args, **kwargs):
            instance.logger = self.mock_logger
            instance.email_app_name = 'outlook.application'
            instance.namespace_name = 'MAPI'
            instance.display_window = args[0] if args else kwargs.get('display_window', False)
            instance.send_emails = args[1] if len(args) > 1 else kwargs.get('send_emails', False)
            instance.auto_send = kwargs.get('auto_send', False)

        self.patcher_emailer_init = patch('PyEmailerAJM.py_emailer_ajm.EmailerInitializer.__init__', side_effect=mock_init, autospec=True)
        self.patcher_emailer_init.start()

        self.patcher_searcher_factory = patch('PyEmailerAJM.py_emailer_ajm.SearcherFactory')
        self.mock_searcher_factory = self.patcher_searcher_factory.start()
        self.mock_searcher = MagicMock()
        self.mock_searcher_factory.return_value.get_searcher.return_value = self.mock_searcher
        
        self.patcher_email_handler_init = patch('PyEmailerAJM.continuous_monitor.backend.continuous_monitor_base.ContinuousMonitorBase.email_handler_init')
        self.patcher_email_handler_init.start()

        self.patcher_signature = patch('PyEmailerAJM.py_emailer_ajm.PyEmailer.email_signature', new_callable=PropertyMock)
        self.mock_signature = self.patcher_signature.start()
        self.mock_signature.return_value = "Andrew Full"

        class ConcreteNonEmail(NonEmailTriggerCMAS):
            ADMIN_EMAIL = ['test@example.com']
            ADMIN_EMAIL_LOGGER = ['test@example.com']
            def _classify_and_process(self, **kwargs):
                pass
        
        self.ConcreteNonEmail = ConcreteNonEmail

    def tearDown(self):
        patch.stopall()

    def test_response_body_formatting_non_email(self):
        instance = self.ConcreteNonEmail(display_window=False, send_emails=True, dev_mode=True)
        body = instance.response_body
        self.assertIn("There is SOMETHING that requires attention", body)
        self.assertIn("Dear test,", body)

    def test_GetMessages_returns_empty_list(self):
        instance = self.ConcreteNonEmail(display_window=False, send_emails=True, dev_mode=True)
        self.assertEqual(instance.GetMessages(), [])
        self.mock_logger.debug.assert_called()

    def test_setup_snooze_tracker_helper_returns_none(self):
        instance = self.ConcreteNonEmail(display_window=False, send_emails=True, dev_mode=True)
        self.assertIsNone(instance._setup_snooze_tracker_helper())
        self.mock_logger.debug.assert_called()

if __name__ == '__main__':
    unittest.main()
