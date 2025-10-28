from typing import Union

from ..backend.errs import UnrecognizedEmailError
from ..backend.enums import EmailMsgImportanceLevel
from abc import abstractmethod
from os.path import isfile, isabs, abspath, join
from tempfile import gettempdir

import win32com.client as win32
# noinspection PyUnresolvedReferences
from pywintypes import com_error
import datetime
import extract_msg
from bs4 import BeautifulSoup
from logging import Logger, getLogger, warning, info


class _BasicMsgProperties:
    def __init__(self, email_item: win32.CDispatch):
        self.email_item = email_item

    @classmethod
    @abstractmethod
    def _validate_and_add_attachments(cls, email_item: win32.CDispatch, attachment_list: list = None):
        ...

    @property
    def sender(self):
        if hasattr(self.email_item, 'SenderEmailType') and self.email_item.SenderEmailType == 'EX':
            return self.email_item.Sender.GetExchangeUser().PrimarySmtpAddress
        # return self.email_item.Sender if hasattr(self.email_item, 'Sender') else self.email_item.sender
        else:
            return (self.email_item.SenderEmailAddress
                    if hasattr(self.email_item, 'SenderEmailAddress')
                    else self.email_item.Sender)

    @property
    def sender_email_type(self):
        if hasattr(self.email_item, 'SenderEmailType'):
            return self.email_item.SenderEmailType
        info("\'SenderEmailType\' attribute not found. Defaulting to 'SMTP' for email type.")
        return "SMTP"

    @property
    def sender_name(self):
        return self.email_item.Sender if hasattr(self.email_item, 'Sender') else self.email_item.sender

    @property
    def to(self):
        return self.email_item.To if hasattr(self.email_item, 'To') else self.email_item.to

    @property
    def cc(self):
        return self.email_item.CC if hasattr(self.email_item, 'CC') else self.email_item.cc

    @property
    def subject(self):
        return self.email_item.Subject if hasattr(self.email_item, 'Subject') else self.email_item.subject

    @property
    def received_time(self):
        #not_future = self.email_item.ReceivedTime.year < datetime.datetime.now().year
        return self.email_item.ReceivedTime #if not_future else None

    @property
    def body(self):
        return self.email_item.HTMLBody if hasattr(self.email_item, 'HTMLBody') else self.email_item.htmlBody

    @property
    def attachments(self):
        return self.email_item.Attachments

    @attachments.setter
    def attachments(self, value: list):
        self._validate_and_add_attachments(self.email_item, value)

    @property
    def importance(self):
        return self.email_item.Importance

    @importance.setter
    def importance(self, value: Union[EmailMsgImportanceLevel, str, int]):
        if value in EmailMsgImportanceLevel or value in [x.name for x in EmailMsgImportanceLevel]:
            if isinstance(value, str):
                value = EmailMsgImportanceLevel[value].value
            elif isinstance(value, EmailMsgImportanceLevel):
                value = value.value
            elif isinstance(value, int):
                pass
            else:
                raise TypeError(f"Invalid importance level: {value}")
        self.email_item.Importance = value


class Msg(_BasicMsgProperties):
    def __init__(self, email_item: win32.CDispatch or extract_msg.Message, **kwargs):
        super().__init__(email_item)
        self._logger: Logger = kwargs.get('logger', getLogger(__name__))
        self.send_success = False

    def __call__(self, *args, **kwargs):
        return self.email_item

    @classmethod
    def SetupMsg(cls, sender, recipient, subject, body, email_item: win32.CDispatch, attachments: list = None, **kwargs):
        email_item.To = recipient
        email_item.Sender = sender
        email_item.Subject = subject
        email_item.HtmlBody = body
        email_item.cc = kwargs.get('cc', '')
        email_item.Bcc = kwargs.get('bcc', '')

        cls._validate_and_add_attachments(email_item, attachments)
        return cls(email_item, **kwargs)

    @classmethod
    def _validate_and_add_attachments(cls, email_item: win32.CDispatch, attachment_list: list = None):
        """ Validate and attach files to the email_item. """
        if not attachment_list:
            # warning("No attachments detected")
            return

        if not isinstance(attachment_list, list):
            raise TypeError("Attachments must be provided as a list")

        def _absolute_file_path(file_path):
            """Returns absolute path if valid; raises FileNotFoundError otherwise."""
            if not isabs(file_path):
                file_path = abspath(file_path)
            if not isfile(file_path):
                raise FileNotFoundError(f"File {file_path} could not be attached.")
            return file_path

        for attachment in attachment_list:
            email_item.attachments.Add(_absolute_file_path(attachment))

    def SaveAllEmailAttachments(self, save_dir_path):
        all_attachment_paths = set()
        for attachment in self.attachments:
            full_save_path = join(save_dir_path, str(attachment))
            try:
                attachment.SaveAsFile(full_save_path)
                all_attachment_paths.add(full_save_path)
                self._logger.debug(f"{full_save_path} saved from email with subject {self.subject}")
            except Exception as e:
                self._logger.error(e, exc_info=True)
                raise e
        return all_attachment_paths

    def display(self):
        # print(f"Displaying the email in {self.email_app_name}, this window might open minimized.")
        # self._logger.info(f"Displaying the email in {self.email_app_name}, this window might open minimized.")
        try:
            self().Display(True)
        except Exception as e:
            self._logger.error(e, exc_info=True)
            raise e

    def send(self):
        try:
            # if the send fails, self.to is NULL, so this needs to be saved in a local variable
            attempted_recipient = self.to
            self.send_success = False
            self._logger.debug(f"Sending email to {attempted_recipient}")
            self().Send()
            # print(f"Mail sent to {self._recipient}")
            self.send_success = True
            self._logger.info(f"Mail successfully sent to {attempted_recipient}")
        except Exception as e:
            if isinstance(e, com_error):
                if e.args[2][0] == 4096:
                    try:
                        raise UnrecognizedEmailError(err_msg=f'{self.to} is not a valid email address. ') from None
                    except UnrecognizedEmailError as e:
                        self._logger.error(e, exc_info=True)
                        return

                self._logger.error(e.args[2][2], exc_info=True)
            else:
                self._logger.error(e, exc_info=True)
            raise e

    def _ValidateResponseMsg(self):
        if isinstance(self(), win32.CDispatch):
            self._logger.debug("passed in msg is CDispatch instance")
        if hasattr(self(), 'HtmlBody') or hasattr(self(), 'htmlBody'):
            self._logger.debug("passed in msg has 'HtmlBody' or 'htmlBody' attr")

        if (not isinstance(self(), win32.CDispatch)
                or not hasattr(self(), ('HtmlBody' or 'htmlBody'))):
            raise AttributeError("msg attr must have 'HtmlBody' attr AND be a CDispatch instance")
        return self()

    def _msg_is_recent(self, recent_days_cap=1):
        if self.received_time is not None:
            abs_diff = abs(self.received_time - datetime.datetime.now(tz=self.received_time.tzinfo))
            return abs_diff <= datetime.timedelta(days=recent_days_cap)
        print(f"msg with subject \'{self.email_item.Subject}\' has no received time. defaulting to false")
        self._logger.debug(f"msg with subject \'{self.email_item.Subject}\' has no received time. defaulting to false")
        return False

    def return_as_failed_send(self):
        return FailedMsg(self())


class FailedMsg(Msg):
    ERR_SKIP_STRING = "err {}: skipping this message"
    DEFAULT_TEMP_SAVE_PATH = gettempdir()

    def _message_filter_checks(self, **kwargs) -> bool:
        recent_days_cap = kwargs.get('recent_days_cap', 1)
        return self._msg_is_recent(recent_days_cap)

    def _fetch_failed_msg_details(self, **kwargs):
        temp_attachment_save_path = kwargs.get('temp_attachment_save_path',
                                               self.__class__.DEFAULT_TEMP_SAVE_PATH)
        try:
            attachment_msg_path = self.SaveAllEmailAttachments(temp_attachment_save_path)
            print('saved_attachments')
        except Exception as e:
            self._logger.warning(self.__class__.ERR_SKIP_STRING.format(f'({e})'))
            return e
        if len(attachment_msg_path) == 1:
            return next(iter(attachment_msg_path))
        return attachment_msg_path

    def process_failed_msg(self, post_master_msg, **kwargs):
        recent_days_cap = kwargs.get('recent_days_cap', 1)
        try:
            self.email_item = post_master_msg
            self._ValidateResponseMsg()
        except AttributeError as e:
            self._logger.warning(self.__class__.ERR_SKIP_STRING.format(f'({e})'))
            return e, None, None

        if self._msg_is_recent(recent_days_cap):
            attachment_msg = self._fetch_failed_msg_details()
            if isinstance(attachment_msg, Exception):
                return attachment_msg, None, None
            else:
                if isinstance(attachment_msg, str):
                    fmd = _FailedMessageDetails.extract_msg_from_attachment(attachment_msg)
                    return fmd.process_failed_details_msg() #self._process_failed_details_msg(attachment_msg)
        return None, None, None


class _FailedMessageDetails(FailedMsg):
    @classmethod
    def extract_msg_from_attachment(cls, parent_msg: str):
        return cls(extract_msg.Message(parent_msg))

    def _extract_from_failed_details_msg(self, para):
        email_of_err = para.findNext('p').get_text().strip().split('(')[0].strip()
        err_reason = para.findNext('p').findNext('p').get_text()
        send_time = self().date.ctime()
        failed_subject = self.subject

        err_details = {'email_of_err': email_of_err, 'err_reason': err_reason,
                       'send_time': send_time, 'failed_subject': failed_subject}
        # print(f"Email of err: {email_of_err},\nErr reason: {err_reason}\nSend time: {send_time}")
        return err_details #email_of_err, err_reason, send_time

    def process_failed_details_msg(self, **kwargs):
        detail_marker_string = kwargs.get('detail_marker_string',
                                          "Delivery has failed to these recipients or groups:")

        soup = BeautifulSoup(self.body, features="html.parser")

        all_p = soup.find_all(name='p')  # , attrs={'class': 'MsoNormal'})

        for para in all_p:
            if detail_marker_string in para.get_text():
                return {** self._extract_from_failed_details_msg(para)}
        return None, None, None
