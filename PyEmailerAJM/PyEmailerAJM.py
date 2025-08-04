#! python3
"""
PyEmailerAJM.py

install win32 with pip install pywin32
"""
from abc import abstractmethod
# imports
from os import environ
from os.path import isfile, abspath, isabs, join, isdir
from tempfile import gettempdir

# install win32 with pip install pywin32
import win32com.client as win32
# This is installed as part of pywin32
# noinspection PyUnresolvedReferences
from pythoncom import com_error
from logging import Logger
from email_validator import validate_email, EmailNotValidError
import questionary
# this is usually thrown when questionary is used in the dev/Non Win32 environment
from prompt_toolkit.output.win32 import NoConsoleScreenBufferError
import warnings
import functools


def deprecated(reason: str = ""):
    """
    Decorator that marks a function or method as deprecated.

    :param reason: Optional message to explain what to use instead
                   or when the feature will be removed.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            message = f"Function '{func.__name__}' is deprecated."
            if reason:
                message += f" {reason}"
            warnings.warn(message, category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator


class EmailerNotSetupError(Exception):
    ...


class DisplayManualQuit(Exception):
    ...


class _SubjectSearcher:
    @abstractmethod
    def GetMessages(self):
        ...

    def find_messages_by_subject(self, search_subject: str, include_fw: bool = True, include_re: bool = True,
                                 partial_match_ok: bool = False) -> list:
        """Returns a list of messages matching the given subject, ignoring prefixes based on flags."""

        # Constants for prefixes
        FW_PREFIXES = ['FW:', 'FWD:']
        RE_PREFIX = 'RE:'

        # Normalize search subject
        normalized_subject = self._normalize_subject(search_subject)
        matched_messages = []
        print("partial match ok: ", partial_match_ok)

        for message in self.GetMessages():
            normalized_message_subject = self._normalize_subject(message.Subject)

            if (self._is_exact_match(normalized_message_subject, normalized_subject) or
                    (partial_match_ok and self._is_partial_match(normalized_message_subject,
                                                                 normalized_subject))):
                matched_messages.append(message)
                continue

            if include_fw and self._matches_prefix(normalized_message_subject, FW_PREFIXES, normalized_subject,
                                                   partial_match_ok):
                matched_messages.append(message)
                continue

            if include_re and self._matches_prefix(normalized_message_subject, [RE_PREFIX], normalized_subject,
                                                   partial_match_ok):
                matched_messages.append(message)

        return matched_messages

    @staticmethod
    def _normalize_subject(subject: str) -> str:
        """Normalize the given subject by converting to lowercase and stripping whitespace."""
        return subject.lower().strip()

    def _matches_prefix(self, message_subject: str, prefixes: list, search_subject: str,
                        partial_match_ok: bool = False) -> bool:
        """Checks if the message subject matches the search subject after removing a prefix."""
        for prefix in prefixes:
            if message_subject.startswith(prefix.lower()):
                stripped_subject = message_subject.split(prefix.lower(), 1)[1].strip()
                return (self._is_exact_match(stripped_subject, search_subject) if not partial_match_ok
                        else self._is_partial_match(stripped_subject, search_subject))
        return False

    @staticmethod
    def _is_exact_match(message_subject: str, search_subject: str) -> bool:
        """Checks if the subject matches exactly."""
        return message_subject == search_subject

    @staticmethod
    def _is_partial_match(message_subject: str, search_subject: str) -> bool:
        return search_subject in message_subject


class PyEmailer(_SubjectSearcher):
    # the email tab_char
    tab_char = '&emsp;'
    signature_dir_path = join((environ['USERPROFILE']),
                              'AppData\\Roaming\\Microsoft\\Signatures\\')

    DisplayEmailSendTrackingWarning = "THIS TYPE OF SEND CANNOT BE DETECTED FOR SEND SUCCESS AUTOMATICALLY."

    INBOX_ID = 6
    SENT_ITEMS_ID = 5
    DRAFTS_ID = 16
    DELETED_ITEMS_ID = 3
    OUTBOX_ID = 4

    DEFAULT_TEMP_SAVE_PATH = gettempdir()

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
        self._current_user_email = None

        self._recipient = None
        self._subject = None
        self._text = None
        self.read_folder = None

        try:
            if self.email_app_name.lower().startswith('outlook'):
                self.email_app = win32.Dispatch(self.email_app_name)
                self.namespace = self.email_app.GetNamespace('MAPI')
                self._logger.debug("MAPI namespace in use.")
            else:
                self.email_app = win32.Dispatch(self.email_app_name)
                self.namespace = None
            self.email = self.email_app.CreateItem(0)
        except com_error as e:
            self._logger.error(e, exc_info=True)
            raise e

        self._email_signature = None
        self._send_success = False
        self.email_sig_filename = email_sig_filename

    @property
    def current_user_email(self):
        if self.email_app_name.lower().startswith('outlook'):
            self._current_user_email = (
                self.namespace.Application.Session.CurrentUser.AddressEntry.GetExchangeUser().PrimarySmtpAddress)
        return self._current_user_email

    @current_user_email.setter
    def current_user_email(self, value):
        try:
            if validate_email(value, check_deliverability=False):
                self._current_user_email = value
        except EmailNotValidError as e:
            self._logger.error(e, exc_info=True)
            value = None
        self._current_user_email = value

    @property
    def email_signature(self):
        return self._email_signature

    @email_signature.getter
    def email_signature(self):
        if self.email_sig_filename:
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
        else:
            self._email_signature = None

        return self._email_signature

    @property
    def send_success(self):
        return self._send_success

    @send_success.setter
    def send_success(self, value):
        self._send_success = value

    def _display_tracking_warning_confirm(self):
        # noinspection PyBroadException
        try:
            q = questionary.confirm(f"{self.DisplayEmailSendTrackingWarning}. Do you understand?",
                                    default=False, auto_enter=False).ask()
            return q
        except Exception as e:
            # TODO: slated for removal
            # this is here purely as a compatibility thing, to be taken out later.
            self._logger.warning(e)
            self._logger.warning("Defaulting to basic y/n prompt.")
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

    def _GetReadFolder(self, email_dir_index: int = INBOX_ID):
        # 6 = inbox
        self.read_folder = self.namespace.GetDefaultFolder(email_dir_index)
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

    @deprecated("use find_messages_by_subject instead")
    def FindMsgBySubject(self, subject: str, forwarded_message_match: bool = True,
                         reply_msg_match: bool = True, partial_match_ok: bool = False):
        return self.find_messages_by_subject(subject, include_fw=forwarded_message_match,
                                             include_re=reply_msg_match,
                                             partial_match_ok=partial_match_ok)

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
        try:
            send = questionary.confirm("Send Mail?:", default=False).ask()
            if send:
                self._send()
                return
            elif not send:
                self._logger.info(f"Mail not sent to {self._recipient}")
                print(f"Mail not sent to {self._recipient}")
                q = questionary.confirm("do you want to quit early?", default=False).ask()
                if q:
                    print("ok quitting!")
                    self._logger.warning("Quitting early due to user input.")
                    exit(-1)
                else:
                    return
        except com_error as e:
            self._logger.error(e, exc_info=True)
        except NoConsoleScreenBufferError as e:
            # TODO: slated for removal
            # this is here purely as a compatibility thing, to be taken out later.
            self._logger.warning(e)
            self._logger.warning("defaulting to basic input style...")
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

    emailer = PyEmailer(display_window=False, send_emails=True, auto_send=False)

    x = emailer.find_messages_by_subject("Timecard", partial_match_ok=False, include_re=False)
    print([m.Subject for m in x])

    # r_dict = {
    #     "subject": f"TEST: Your TEST "
    #                f"agreement expires in 30 days or less!",
    #     "text": "testing to see if the attachment works",
    #     "recipient": 'test',
    #     "attachments": []
    # }
    # # &emsp; is the tab character for emails
    # emailer.SetupEmail(**r_dict)  # recipient="test", subject="test subject", text="test_body")
    # emailer.SendOrDisplay()
