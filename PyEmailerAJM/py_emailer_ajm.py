#! python3
"""
py_emailer_ajm.py

install win32 with pip install pywin32
"""
# imports
from os import environ
from os.path import isfile, join, isdir
from tempfile import gettempdir

# install win32 with pip install pywin32
import win32com.client as win32

# This is installed as part of pywin32
# noinspection PyUnresolvedReferences
from pythoncom import com_error
from logging import Logger, basicConfig, StreamHandler, FileHandler, getLogger
from email_validator import validate_email, EmailNotValidError
import questionary
# this is usually thrown when questionary is used in the dev/Non Win32 environment
# noinspection PyProtectedMember
from prompt_toolkit.output.win32 import NoConsoleScreenBufferError

from PyEmailerAJM import (EmailerNotSetupError, DisplayManualQuit,
                          deprecated,
                          Msg, FailedMsg)
from PyEmailerAJM.backend import BasicEmailFolderChoices, PyEmailerLogger
from PyEmailerAJM.searchers import SubjectSearcher


class EmailerInitializer:
    """
        A class responsible for initializing and handling email-related operations through a specified
        email application and namespace. The class uses COM (Component Object Model) to interact with
        the email application and provides mechanisms for logging and email management.

        Attributes:
            DEFAULT_EMAIL_APP_NAME (str): Default application name for email, set to 'outlook.application'.
            DEFAULT_NAMESPACE_NAME (str): Default namespace name for the email application, set to 'MAPI'.
    """
    DEFAULT_EMAIL_APP_NAME = 'outlook.application'
    DEFAULT_NAMESPACE_NAME = 'MAPI'

    def __init__(self, display_window: bool,
                 send_emails: bool, logger: Logger = None,
                 auto_send: bool = False,
                 email_app_name: str = DEFAULT_EMAIL_APP_NAME,
                 namespace_name: str = DEFAULT_NAMESPACE_NAME, **kwargs):
        if logger:
            self.logger = logger
        else:
            self._elog = PyEmailerLogger(**kwargs)
            self.logger = self._elog()
        # print("Dummy logger in use!")

        self.email_app_name = email_app_name
        self.namespace_name = namespace_name

        self.email_app, self.namespace, self.email = self.initialize_email_item_app_and_namespace()

        self.display_window = display_window
        self.auto_send = auto_send
        self.send_emails = send_emails

    def initialize_new_email(self):
        if hasattr(self, 'email_app') and self.email_app is not None:
            self.email = Msg(self.email_app.CreateItem(0), logger=self.logger)
            return self.email
        raise AttributeError("email_app is not defined. Run 'initialize_email_item_app_and_namespace' first")

    def initialize_email_item_app_and_namespace(self):
        try:
            email_app, namespace = self._setup_email_app_and_namespace()
            email = self.initialize_new_email()
        except com_error as e:
            self.logger.error(e, exc_info=True)
            raise e
        return email_app, namespace, email

    def _setup_email_app_and_namespace(self):
        self.email_app = win32.Dispatch(self.email_app_name)

        self.logger.debug(f"{self.email_app_name} app in use.")
        self.namespace = self.email_app.GetNamespace(self.namespace_name)

        self.logger.debug(f"{self.namespace_name} namespace in use.")
        return self.email_app, self.namespace


class PyEmailer(EmailerInitializer, SubjectSearcher):
    """
    The `PyEmailer` class is designed for managing and handling email-related operations.
    It initializes email client settings, manages email folders, handles email messages,
    and supports common email-related functionalities such as tracking, setting up emails,
    and saving attachments.
    The class extends functionality from `EmailerInitializer` and `SubjectSearcher`.

    Attributes:
    - `tab_char`: Specifies the tab character to be used.
    - `signature_dir_path`: Defines the file path to the email signature directory.
    - `DisplayEmailSendTrackingWarning`: Warning message displayed when email tracking cannot ensure delivery success.
    - `FAILED_SEND_LOGGER_STRING`: Format string for logging failed email sends.
    - `DEFAULT_TEMP_SAVE_PATH`: Default temporary directory for saving temporary files.
    - `VALID_EMAIL_FOLDER_CHOICES`: List of valid folder indices for email directories.

    Methods:
    - `__init__`: Initializes an instance of the `PyEmailer` class with specified settings and optional arguments.
    - `current_user_email`: Getter and setter for retrieving or setting the current user's email address.
    - `email_signature`: Property that retrieves the email signature from a specified signature file.
    - `send_success`: Getter and setter to track the send status of an email.
    - `_display_tracking_warning_confirm`: Handles display and confirmation of email tracking warnings interactively.
    - `display_tracker_check`: Prompts the user to confirm understanding of the email tracking warning; raises an exception if canceled.
    - `_get_default_folder_for_email_dir`: Retrieves the default folder for a specified email directory index.
    - `_GetReadFolder`: Helper method that retrieves the specified email folder or default folder, along with an optional subfolder.
    - `GetMessages`: Retrieves messages from a specified folder or the currently set folder.
    - `GetEmailMessageBody`: Deprecated method to retrieve the body of an email message; use the `Msg` class's `body` attribute instead.
    - `FindMsgBySubject`: Deprecated method to search for messages by subject; use `find_messages_by_subject`.
    - `SaveAllEmailAttachments`: Saves all attachments of a specified email to a given directory path.
    - `SetupEmail`: Configures an email with recipient, subject, text, and optional attachments.
    - `_manual_send_loop`: Handles an interactive loop to allow the manual sending of an email.

    This class provides comprehensive methods and attributes for streamlining email-related workflows.
    It emphasizes interaction, logging, and error handling for robust functionality.
    """
    # the email tab_char
    tab_char = '&emsp;'
    signature_dir_path = join((environ['USERPROFILE']),
                              'AppData\\Roaming\\Microsoft\\Signatures\\')

    DisplayEmailSendTrackingWarning = "THIS TYPE OF SEND CANNOT BE DETECTED FOR SEND SUCCESS AUTOMATICALLY."
    FAILED_SEND_LOGGER_STRING = "{num} confirmed failed send(s) found in the last {recent_days_cap} day(s)."

    DEFAULT_TEMP_SAVE_PATH = gettempdir()
    VALID_EMAIL_FOLDER_CHOICES = [x for x in BasicEmailFolderChoices]

    def __init__(self, display_window: bool, send_emails: bool, logger: Logger = None, email_sig_filename: str = None,
                 auto_send: bool = False, email_app_name: str = EmailerInitializer.DEFAULT_EMAIL_APP_NAME,
                 namespace_name: str = EmailerInitializer.DEFAULT_NAMESPACE_NAME, **kwargs):

        super().__init__(display_window, send_emails, logger, auto_send, email_app_name, namespace_name, **kwargs)
        self._setup_was_run = False
        self._current_user_email = None

        self.read_folder = None

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
            self.logger.error(e, exc_info=True)
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
                    self.logger.warning(e)
                    self._email_signature = None

            if isfile(signature_full_path):
                with open(signature_full_path, 'r', encoding='utf-16') as f:
                    self._email_signature = f.read().strip()
            else:
                try:
                    raise FileNotFoundError(f"{signature_full_path} does not exist.")
                except FileNotFoundError as e:
                    self.logger.warning(e)
                    self._email_signature = None
        else:
            self._email_signature = None
            self.logger.info("email_sig_filename not specified, no email signature will be attached.")

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
            self.logger.warning(e)
            self.logger.warning("Defaulting to basic y/n prompt.")
            while True:
                q = input(f"{self.DisplayEmailSendTrackingWarning}. Do you understand? (y/n): ").lower().strip()
                if q == 'y':
                    self.logger.warning(self.DisplayEmailSendTrackingWarning)
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
                    self.logger.error(e, exc_info=True)
                    raise e

    def _get_default_folder_for_email_dir(self, email_dir_index: int = None, **kwargs):
        # 6 = inbox
        if email_dir_index in self.__class__.VALID_EMAIL_FOLDER_CHOICES:
            self.read_folder = self.namespace.GetDefaultFolder(email_dir_index)
            return self.read_folder
        else:
            try:
                raise ValueError(f"email_dir_index must be one of {self.__class__.VALID_EMAIL_FOLDER_CHOICES}")
            except ValueError as e:
                self.logger.error(e, exc_info=True)
                raise e

    def _GetReadFolder(self, email_dir_index: int = None, **kwargs):
        """
        :param email_dir_index: Specifies the email directory index to be accessed. Defaults to None.
        :type email_dir_index: int, optional
        :param kwargs: Additional optional arguments that may be passed. Can include `subfolder_name` to specify a subfolder name, defaulting to 'Inbox'.
        :type kwargs: dict
        :return: The folder specified either by the email directory index or the default folder along with the subfolder if applicable.
        :rtype: object
        """
        subfolder_name = kwargs.get('subfolder_name', 'Inbox')
        if not email_dir_index:
            email_dir_index = BasicEmailFolderChoices.INBOX
            self.logger.debug(f">>> email_dir_index not specified, defaulting to '{email_dir_index}' folder. <<<")
        if not isinstance(email_dir_index, int):
            self.logger.debug(f">>> email_dir_index is not an int, "
                               f"defaulting to {email_dir_index} folder and {subfolder_name} subfolder. <<<")
            return self.namespace.Folders[email_dir_index].Folders[subfolder_name]

        else:
            return self._get_default_folder_for_email_dir(email_dir_index)

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
                self.logger.error(e, exc_info=True)
                raise e
        return [Msg(m, logger=self.logger) for m in self.read_folder.Items]

    @deprecated("use Msg classes body attribute instead")
    def GetEmailMessageBody(self, msg):
        """message = messages.GetLast()"""
        body_content = msg.body
        if body_content:
            return body_content
        else:
            try:
                raise ValueError("This message has no body.")
            except ValueError as e:
                self.logger.error(e, exc_info=True)
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
                self.logger.debug(f"{full_save_path} saved from email with subject {msg.subject}")
            except Exception as e:
                self.logger.error(e, exc_info=True)
                raise e

    def SetupEmail(self, recipient: str, subject: str, text: str, attachments: list = None, **kwargs):
        self.email = self.email.SetupMsg(sender=self.current_user_email, email_item=self.email(),
                                         recipient=recipient, subject=subject, body=text, attachments=attachments,
                                         logger=self.logger, **kwargs)
        self._setup_was_run = True
        return self.email

    def _manual_send_loop(self):
        try:
            send = questionary.confirm("Send Mail?:", default=False).ask()
            if send:
                self.email.send()
                return
            elif not send:
                self.logger.info(f"Mail not sent to {self.email.to}")
                print(f"Mail not sent to {self.email.to}")
                q = questionary.confirm("do you want to quit early?", default=False).ask()
                if q:
                    print("ok quitting!")
                    self.logger.warning("Quitting early due to user input.")
                    exit(-1)
                else:
                    return
        except com_error as e:
            self.logger.error(e, exc_info=True)
        except NoConsoleScreenBufferError as e:
            # TODO: slated for removal
            # this is here purely as a compatibility thing, to be taken out later.
            self.logger.warning(e)
            self.logger.warning("defaulting to basic input style...")
            while True:
                yn = input("Send Mail? (y/n/q): ").lower()
                if yn == 'y':
                    self.email.send()
                    break
                elif yn == 'n':
                    self.logger.info(f"Mail not sent to {self.email.to}")
                    print(f"Mail not sent to {self.email.to}")
                    break
                elif yn == 'q':
                    print("ok quitting!")
                    self.logger.warning("Quitting early due to user input.")
                    exit(-1)
                else:
                    print("Please choose \'y\', \'n\' or \'q\'")

    def SendOrDisplay(self, print_ready_msg: bool = False):
        if self._setup_was_run:
            if print_ready_msg:
                print(f"Ready to send/display mail to/for {self.email.to}...")
            self.logger.info(f"Ready to send/display mail to/for {self.email.to}...")
            if self.send_emails and self.display_window:
                send_and_display_warning = ("Sending email while also displaying the email "
                                            "in the app is not possible. Defaulting to Display only")
                # print(send_and_display_warning)
                self.logger.warning(send_and_display_warning)
                self.send_emails = False
                self.display_window = True

            if self.send_emails:
                if self.auto_send:
                    self.logger.info("Sending emails with auto_send...")
                    self.email.send()

                else:
                    self._manual_send_loop()

            elif self.display_window:
                self.email.display()
            else:
                both_disabled_warning = ("Both sending and displaying the email are disabled. "
                                         "No errors were encountered.")
                self.logger.warning(both_disabled_warning)
                # print(both_disabled_warning)
        else:
            try:
                raise EmailerNotSetupError("Setup has not been run, sending or displaying an email cannot occur.")
            except EmailerNotSetupError as e:
                self.logger.error(e, exc_info=True)
                raise e

    @staticmethod
    def _fmsg_is_no_info_or_err(info):
        return (any(isinstance(x, Exception) for x in info)
                or all(isinstance(x, type(None)) for x in info))

    def get_failed_sends(self, fail_string_marker: str = 'undeliverable', partial_match_ok: bool = True, **kwargs):
        failed_sends = []
        recent_days_cap = kwargs.get('recent_days_cap', 1)
        self.GetMessages(BasicEmailFolderChoices.INBOX)

        msg_candidates = self.FindMsgBySubject(fail_string_marker, partial_match_ok=partial_match_ok)

        if msg_candidates:
            msg_candidates = [FailedMsg(m) for m in msg_candidates]
            self.logger.info(f"{len(msg_candidates)} 'failed send' candidates found.")
            self.logger.info("mutating msg_candidates (Msg instances) into FailedMsg instances.")

            for m in msg_candidates:
                failed_info = m.process_failed_msg(m(), recent_days_cap=recent_days_cap)

                if self._fmsg_is_no_info_or_err(failed_info):
                    continue
                else:
                    failed_sends.append({'postmaster_email': m.sender,
                                         'err_info': failed_info})
        results_string = self.__class__.FAILED_SEND_LOGGER_STRING.format(num=len(failed_sends),
                                                                         recent_days_cap=recent_days_cap)
        if (not self.logger.hasHandlers() or not any([isinstance(x, StreamHandler)
                                                       for x in self.logger.handlers])):
            print(results_string)
        self.logger.info(results_string)
        return failed_sends


def __failed_sends_test(emailer):
    failed_sends = emailer.get_failed_sends(recent_days_cap=1)
    fs_results = ([(x.get('err_info').get('send_time'),
                    x.get('err_info').get('failed_subject'))
                   for x in failed_sends]
                  if failed_sends else "no failed sends found")
    print(fs_results)


def __setup_and_send_test(emailer):
    emailer.SetupEmail(subject="TEST: Your TEST agreement expires in 30 days or less!",
                       recipient='amcsparron@albanyny.gov',
                       text="testing to see anything works", bcc='amcsparron@albanyny.gov')
    emailer.SendOrDisplay()


if __name__ == "__main__":
    module_name = __file__.split('\\')[-1].split('.py')[0]

    em = PyEmailer(display_window=False, send_emails=True, auto_send=False, use_default_logger=False)
    m = em.find_messages_by_subject('Andrew', partial_match_ok=True)
    print([type(x) for x in m])
    # __setup_and_send_test(em)
    # __failed_sends_test(em)
    x = em.find_messages_by_subject("GIS Request", partial_match_ok=True)
    # [x.name for x in m.ItemProperties]
    print([(m.__class__, m.sender, m.sender_email_type, m.subject)
           for m in [Msg(y) for y in x]])  # for m in x])
    # property_accessor = x[0].PropertyAccessor
    # print(x[0].Sender.GetExchangeUser().PrimarySmtpAddress)
    # print(property_accessor.GetProperty("PR_EMAIL_ADDRESS"))

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
