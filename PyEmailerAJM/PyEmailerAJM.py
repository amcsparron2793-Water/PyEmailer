#! python3
"""
PyEmailerAJM.py

install win32 with pip install pywin32
"""
from os import environ
from os.path import isfile, abspath, isabs, join, isdir

# imports

# install win32 with pip install pywin32
import win32com.client as win32
# This is installed as part of pywin32
from pythoncom import com_error
from logging import Logger


class EmailerNotSetupError(Exception):
    ...


class DisplayManualQuit(Exception):
    ...


class PyEmailer:
    # the email tab_char
    tab_char = '&emsp;'
    signature_dir_path = join((environ['USERPROFILE']),
                              'AppData\\Roaming\\Microsoft\\Signatures\\')

    DisplayEmailSendTrackingWarning = "THIS TYPE OF SEND CANNOT BE DETECTED FOR SEND SUCCESS AUTOMATICALLY."

    def __init__(self, display_window: bool,
                 send_emails: bool, logger: Logger = None,
                 email_sig_filename: str = None,
                 auto_send: bool = False,
                 email_app_name: str = 'outlook.application'):

        if logger:
            self._logger = logger
        else:
            self._logger = Logger("DUMMY")
            # print("Dummy logger in use!")

        self.email_app_name = email_app_name

        self.display_window = display_window
        self.auto_send = auto_send
        self.send_emails = send_emails
        self._setup_was_run = False

        self._recipient = None
        self._subject = None
        self._text = None
        self.read_folder = None

        try:
            self.email_app = win32.Dispatch(self.email_app_name)
            self._mapi_ns = self.email_app.GetNamespace('MAPI')
            self.email = self.email_app.CreateItem(0)
        except com_error as e:
            self._logger.error(e, exc_info=True)
            raise e

        self._email_signature = None
        self._send_success = False
        self.email_sig_filename = email_sig_filename

    @property
    def email_signature(self):
        return self._email_signature

    @email_signature.getter
    def email_signature(self):
        signature_full_path = join(self.signature_dir_path, self.email_sig_filename)
        if isdir(self.signature_dir_path):
            pass
        else:
            try:
                raise NotADirectoryError(f"{self.signature_dir_path} does not exist.")
            except NotADirectoryError as e:
                self._logger.warning(e)
                self._email_signature = None

        if isfile(signature_full_path):
            with open(signature_full_path, 'r', encoding='utf-16') as f:
                self._email_signature = f.read().strip()
        else:
            try:
                raise FileNotFoundError(f"{signature_full_path} does not exist.")
            except FileNotFoundError as e:
                self._logger.warning(e)
                self._email_signature = None

        return self._email_signature

    @property
    def send_success(self):
        return self._send_success

    @send_success.setter
    def send_success(self, value):
        self._send_success = value

    def _display_tracking_warning_confirm(self):
        while True:
            q = input(f"{self.DisplayEmailSendTrackingWarning}. Do you understand? (y/n): ").lower().strip()
            if q == 'y':
                self._logger.warning(self.DisplayEmailSendTrackingWarning)
                return True
            elif q == 'n':
                return False
            else:
                print("Please respond with 'y' or 'n'.")

    def display_tracker_check(self) -> bool:
        if self.display_window:
            c = self._display_tracking_warning_confirm()
            if c:
                return c
            else:
                try:
                    raise DisplayManualQuit("User cancelled operation due to DisplayTrackingWarning.")
                except DisplayManualQuit as e:
                    self._logger.error(e, exc_info=True)
                    raise e

    def _GetReadFolder(self, email_dir_index: int = 6):
        # 6 = inbox
        self.read_folder = self._mapi_ns.GetDefaultFolder(email_dir_index)
        return self.read_folder

    def GetMessages(self, folder_index=None):
        if isinstance(folder_index, int):
            self.read_folder = self._GetReadFolder(folder_index)
        elif not folder_index and self.read_folder:
            pass
        elif not folder_index:
            self.read_folder = self._GetReadFolder()
        else:
            try:
                raise TypeError("folder_index must be an integer or self.read_folder must be defined")
            except TypeError as e:
                self._logger.error(e, exc_info=True)
                raise e
        return self.read_folder.Items

    def GetEmailMessageBody(self, msg):
        """message = messages.GetLast()"""
        body_content = msg.body
        if body_content:
            return body_content
        else:
            try:
                raise ValueError("This message has no body.")
            except ValueError as e:
                self._logger.error(e, exc_info=True)
                raise e

    def FindMsgBySubject(self, subject: str, forwarded_message_match: bool = True,
                         reply_msg_match: bool = True) -> list:
        """Matches the message.Subject string to the subject attr string and returns a list of messages.
        If forward_message_match is True than messages are matched without
        regard to if they start with 'FW:' or 'FWD:'

        If reply_msg_match is True than messages are matched without
        regard to if they start with 'RE:'
        """
        matched_messages = []
        subject = subject.lower().strip()
        fw_str = 'FW:'.lower()
        fwd_str = 'FWD:'.lower()
        re_str = 'RE:'.lower()

        for message in self.GetMessages():
            message.Subject = message.Subject.lower()
            if forwarded_message_match:
                if (message.Subject == subject or
                        (message.Subject.startswith(fw_str)
                         and message.Subject.split(fw_str)[1].strip() == subject) or
                        (message.Subject.startswith(fwd_str)
                         and message.Subject.split(fwd_str)[1].strip() == subject)):
                    matched_messages.append(message)
            if reply_msg_match:
                if (message.Subject == subject or
                        (message.Subject.startswith(re_str)
                         and message.Subject.split(re_str)[1].strip() == subject)):
                    matched_messages.append(message)
            else:
                if message.Subject == subject:
                    matched_messages.append(message)

        return matched_messages

    def SaveAllEmailAttachments(self, msg, save_dir_path):
        attachments = msg.Attachments
        for attachment in attachments:
            full_save_path = join(save_dir_path, str(attachment))
            try:
                attachment.SaveAsFile(full_save_path)
                self._logger.debug(f"{full_save_path} saved from email with subject {msg.subject}")
            except Exception as e:
                self._logger.error(e, exc_info=True)
                raise e

    def SetupEmail(self, recipient: str, subject: str, text: str, attachments: list = None):
        def _validate_attachments():
            if attachments:
                if isinstance(attachments, list):
                    for a in attachments:
                        if isfile(a):
                            if isabs(a):
                                self.email.Attachments.Add(a)
                            else:
                                a = abspath(a)
                                if isfile(a):
                                    self.email.Attachments.Add(a)
                                else:
                                    try:
                                        raise FileNotFoundError(f"file {a} could not be attached.")
                                    except FileNotFoundError as e:
                                        self._logger.error(e, exc_info=True)
                                        raise e
                        else:
                            try:
                                raise FileNotFoundError(f"file {a} could not be attached.")
                            except FileNotFoundError as e:
                                self._logger.error(e, exc_info=True)
                                raise e
                else:
                    try:
                        raise TypeError("attachments attribute must be a list")
                    except TypeError as e:
                        self._logger.error(e, exc_info=True)
                        raise e
            else:
                self._logger.debug("no attachments detected")

        try:
            # set the params
            _validate_attachments()
            self.email.To = recipient
            self.email.Subject = subject
            self.email.HtmlBody = text

            self._recipient = self.email.To
            self._subject = self.email.Subject
            self._text = self.email.HtmlBody

            # print("New email set up successfully.")
            self._logger.info("New email set up successfully. see debug for details")
            self._logger.debug(f"Email recipient {recipient}, Subject {subject}, Message body {text}")
            self._setup_was_run = True
            return self.email

        except Exception as e:
            self._logger.error(e, exc_info=True)
            raise e

    def _display(self):
        # print(f"Displaying the email in {self.email_app_name}, this window might open minimized.")
        self._logger.info(f"Displaying the email in {self.email_app_name}, this window might open minimized.")
        try:
            self.email.Display(True)
        except Exception as e:
            self._logger.error(e, exc_info=True)
            raise e

    def _send(self):
        try:
            self.send_success = False
            self.email.Send()
            # print(f"Mail sent to {self._recipient}")
            self.send_success = True
            self._logger.info(f"Mail successfully sent to {self._recipient}")
        except Exception as e:
            self._logger.error(e, exc_info=True)
            raise e

    def _manual_send_loop(self):
        while True:
            yn = input("Send Mail? (y/n/q): ").lower()
            if yn == 'y':
                self._send()
                break
            elif yn == 'n':
                self._logger.info(f"Mail not sent to {self._recipient}")
                print(f"Mail not sent to {self._recipient}")
                break
            elif yn == 'q':
                print("ok quitting!")
                self._logger.warning("Quitting early due to user input.")
                exit(-1)
            else:
                print("Please choose \'y\', \'n\' or \'q\'")

    def SendOrDisplay(self):
        if self._setup_was_run:
            # print(f"Ready to send/display mail to/for {self._recipient}...")
            self._logger.info(f"Ready to send/display mail to/for {self._recipient}...")
            if self.send_emails and self.display_window:
                send_and_display_warning = ("Sending email while also displaying the email "
                                            "in the app is not possible. Defaulting to Display only")
                # print(send_and_display_warning)
                self._logger.warning(send_and_display_warning)
                self.send_emails = False
                self.display_window = True

            if self.send_emails:
                if self.auto_send:
                    self._logger.info("Sending emails with auto_send...")
                    self._send()
                else:
                    self._manual_send_loop()

            elif self.display_window:
                self._display()
            else:
                both_disabled_warning = ("Both sending and displaying the email are disabled. "
                                         "No errors were encountered.")
                self._logger.warning(both_disabled_warning)
                # print(both_disabled_warning)
        else:
            try:
                raise EmailerNotSetupError("Setup has not been run, sending or displaying an email cannot occur.")
            except EmailerNotSetupError as e:
                self._logger.error(e, exc_info=True)
                raise e


if __name__ == "__main__":
    module_name = __file__.split('\\')[-1].split('.py')[0]

    """emailer = PyEmailer(display_window=False, send_emails=True, auto_send=False)

    r_dict = {
        "subject": f"TEST: Your TEST "
                   f"agreement expires in 30 days or less!",
        "text": "testing to see if the attachment works",
        "recipient": 'test',
        "attachments": []
    }
    # &emsp; is the tab character for emails
    emailer.SetupEmail(**r_dict)  # recipient="test", subject="test subject", text="test_body")
    emailer.SendOrDisplay()"""
