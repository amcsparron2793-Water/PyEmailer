import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock

from PyEmailerAJM.py_emailer_ajm import PyEmailer


class TestEmailSignature(unittest.TestCase):
    def setUp(self) -> None:
        # Avoid actual COM/Outlook initialization
        self._init_email_patch = patch(
            'PyEmailerAJM.py_emailer_ajm.EmailerInitializer.initialize_email_item_app_and_namespace',
            return_value=(None, None, MagicMock())
        )
        self._init_email_patch.start()

    def tearDown(self) -> None:
        self._init_email_patch.stop()

    def test_email_signature_utf8_sig_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Prepare a signature file encoded with UTF-8 BOM
            sig_name = 'TestSig.txt'
            sig_path = os.path.join(tmpdir, sig_name)
            content = 'Line 1\nLine 2\n'
            with open(sig_path, 'w', encoding='utf-8-sig') as f:
                f.write(content)

            # Instantiate PyEmailer with overridden signature_dir_path
            class TestEmailer(PyEmailer):
                signature_dir_path = tmpdir + os.sep

            emailer = TestEmailer(display_window=False, send_emails=False, logger=MagicMock(),
                                  email_sig_filename=sig_name)

            # Access property to trigger reading
            sig = emailer.email_signature
            self.assertEqual(sig, content.strip())


if __name__ == '__main__':
    unittest.main()
