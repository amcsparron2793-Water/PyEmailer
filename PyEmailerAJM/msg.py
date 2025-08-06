from os.path import isfile, isabs, abspath, join
from tempfile import gettempdir

import win32com.client as win32
import datetime
import extract_msg
from bs4 import BeautifulSoup
from logging import Logger, getLogger, basicConfig


# TODO: tons of work to do to get this integrated into PyEmailer - specifically with the FailedSend stuff
class Msg:
    def __init__(self, email_item: win32.CDispatch or extract_msg.Message, **kwargs):
        self.email_item = email_item
        if issubclass(self.email_item.__class__, Msg):#, FailedMsg, FailedMessageDetails)):
            self.email_item = self.email_item.email_item
        self._logger: Logger = kwargs.get('logger', getLogger(__name__))
        basicConfig(level='INFO')
        self.send_success = False

    @property
    def sender(self):
        return self.email_item.Sender if hasattr(self.email_item, 'Sender') else self.email_item.sender

    @property
    def to(self):
        return self.email_item.To if hasattr(self.email_item, 'To') else self.email_item.to

    @property
    def subject(self):
        return self.email_item.Subject if hasattr(self.email_item, 'Subject') else self.email_item.subject

    @property
    def body(self):
        return self.email_item.HTMLBody if hasattr(self.email_item, 'HTMLBody') else self.email_item.htmlBody

    @property
    def attachments(self):
        return self.email_item.Attachments

    @attachments.setter
    def attachments(self, value: list):
        self._validate_and_add_attachments(self.email_item, value)

    @classmethod
    def SetupMsg(cls, sender, recipient, subject, body, email_item: win32.CDispatch, attachments: list = None):
        email_item.To = recipient
        email_item.From = sender
        email_item.Subject = subject
        email_item.HtmlBody = body
        cls._validate_and_add_attachments(email_item, attachments)
        return cls(email_item)

    @classmethod
    def _validate_and_add_attachments(cls, email_item: win32.CDispatch, attachments: list = None):
        if attachments:
            if isinstance(attachments, list):
                for a in attachments:
                    if isfile(a):
                        if isabs(a):
                            email_item.attachments.Add(a)
                        else:
                            a = abspath(a)
                            if isfile(a):
                                email_item.attachments.Add(a)
                            else:
                                raise FileNotFoundError(f"file {a} could not be attached.")

                    else:
                        raise FileNotFoundError(f"file {a} could not be attached.")

            else:
                raise TypeError("attachments attribute must be a list")

        else:
            print("no attachments detected")

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

    def _display(self):
        # print(f"Displaying the email in {self.email_app_name}, this window might open minimized.")
        # self._logger.info(f"Displaying the email in {self.email_app_name}, this window might open minimized.")
        try:
            self.email_item.Display(True)
        except Exception as e:
            self._logger.error(e, exc_info=True)
            raise e

    def _send(self):
        try:
            self.send_success = False
            self.email_item.Send()
            # print(f"Mail sent to {self._recipient}")
            self.send_success = True
            self._logger.info(f"Mail successfully sent to {self.to}")
        except Exception as e:
            self._logger.error(e, exc_info=True)
            raise e

    def _ValidateResponseMsg(self):
        if isinstance(self.email_item, win32.CDispatch):
            self._logger.debug("passed in msg is CDispatch instance")
        if hasattr(self.email_item, 'HtmlBody'):
            self._logger.debug("passed in msg has 'HtmlBody' attr")

        if not isinstance(self.email_item, win32.CDispatch) or not hasattr(self.email_item, 'HtmlBody'):
            try:
                raise AttributeError("msg attr must have 'HtmlBody' attr AND be a CDispatch instance")
            except AttributeError as e:
                self._logger.error(e, exc_info=True)
                raise e
        else:
            return self.email_item


class FailedMsg(Msg):
    DEFAULT_TEMP_SAVE_PATH = gettempdir()

    @property
    def received_time(self):
        return self.email_item.ReceivedTime

    def _message_filter_checks(self, **kwargs) -> bool:
        recent_days_cap = kwargs.get('recent_days_cap', 1)
        return self._failed_msg_is_recent(recent_days_cap)

    # TODO: tons of work to do to get this working
    # TODO: make recent_days_cap more accessible to PyEmailer
    def _failed_msg_is_recent(self, recent_days_cap=1):
        abs_diff = abs(self.received_time - datetime.datetime.now(tz=self.received_time.tzinfo))
        return abs_diff <= datetime.timedelta(days=recent_days_cap)

    def _fetch_failed_msg_details(self, **kwargs):
        temp_attachment_save_path = kwargs.get('temp_attachment_save_path',
                                               self.__class__.DEFAULT_TEMP_SAVE_PATH)
        try:
            attachment_msg_path = self.SaveAllEmailAttachments(temp_attachment_save_path)
            print('saved_attachments')
        except Exception as e:
            self._logger.warning("err: skipping this message")
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
            self._logger.warning("err: skipping this message")
            return e, None, None
        if self._failed_msg_is_recent(recent_days_cap):
            attachment_msg = self._fetch_failed_msg_details()
            if isinstance(attachment_msg, Exception):
                return attachment_msg, None, None
            else:
                if isinstance(attachment_msg, str):
                    fmd = FailedMessageDetails.extract_msg_from_attachment(attachment_msg)
                    return fmd.process_failed_details_msg() #self._process_failed_details_msg(attachment_msg)
        return None, None, None


class FailedMessageDetails(FailedMsg):
    @classmethod
    def extract_msg_from_attachment(cls, attachment_msg: str, **kwargs):
        return cls(extract_msg.Message(attachment_msg))

    def process_failed_details_msg(self, **kwargs):
        detail_marker_string = kwargs.get('detail_marker_string',
                                          "Delivery has failed to these recipients or groups:")

        soup = BeautifulSoup(self.body, features="html.parser")

        all_p = soup.find_all(name='p')  # , attrs={'class': 'MsoNormal'})

        for para in all_p:
            if detail_marker_string in para.get_text():
                email_of_err = para.findNext('p').get_text().strip().split('(')[0].strip()
                err_reason = para.findNext('p').findNext('p').get_text()
                send_time = self.email_item.date
                failed_subject = self.subject
                # TODO: implement this so that adding other attrs is easier in the future
                err_details = {'email_of_err': email_of_err, 'err_reason': err_reason,
                               'send_time': send_time, 'failed_subject': failed_subject}
                # print(f"Email of err: {email_of_err},\nErr reason: {err_reason}\nSend time: {send_time}")
                return email_of_err, err_reason, send_time
        return None, None, None
