from os.path import isfile, isabs, abspath, join
from tempfile import gettempdir

import win32com.client as win32
import datetime
import extract_msg
from bs4 import BeautifulSoup


# TODO: tons of work to do to get this integrated into PyEmailer - specifically with the FailedSend stuff
class Msg:
    def __init__(self, email_item: win32.CDispatch):
        self.email_item = email_item
        self._logger = None
        self.send_success = False

    @property
    def sender(self):
        return self.email_item.Sender

    @property
    def to(self):
        return self.email_item.To

    @property
    def subject(self):
        return self.email_item.Subject

    @property
    def body(self):
        return self.email_item.HTMLBody

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
        for attachment in self.attachments:
            full_save_path = join(save_dir_path, str(attachment))
            try:
                attachment.SaveAsFile(full_save_path)
                self._logger.debug(f"{full_save_path} saved from email with subject {self.subject}")
            except Exception as e:
                self._logger.error(e, exc_info=True)
                raise e

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


class FailedMsg(Msg):

    DEFAULT_TEMP_SAVE_PATH = gettempdir()

    def __init__(self, email_item: win32.CDispatch):
        super().__init__(email_item)

# TODO: tons of work to do to get this working
    @staticmethod
    def _failed_msg_is_dam_eap_and_recent(msg, recent_days_cap=1):
        abs_diff = abs(msg.ReceivedTime - datetime.datetime.now(tz=msg.ReceivedTime.tzinfo))
        return (abs_diff <= datetime.timedelta(days=recent_days_cap)
                and ('EAP' in msg.Subject or 'Emergency Action Plan' in msg.Subject))

    def _fetch_failed_msg_details(self, msg, **kwargs):
        temp_attachment_save_path = kwargs.get('temp_attachment_save_path',
                                               self.__class__.DEFAULT_TEMP_SAVE_PATH)
        try:
            attachment_msg_path = self.SaveAllEmailAttachments(temp_attachment_save_path)
            print('saved_attachments')
        except Exception as e:
            self._logger.warning("err: skipping this message")
            return e
        return attachment_msg_path

    @staticmethod
    def _process_failed_details_msg(attachment_msg, **kwargs):
        detail_marker_string = kwargs.get('detail_marker_string', "Delivery has failed to these recipients or groups:")

        failed_details_msg = extract_msg.Message(attachment_msg)

        soup = BeautifulSoup(failed_details_msg.htmlBody, features="html.parser")

        all_p = soup.find_all(name='p')  # , attrs={'class': 'MsoNormal'})

        for para in all_p:
            if detail_marker_string in para.get_text():
                email_of_err = para.findNext('p').get_text().strip().split('(')[0].strip()
                err_reason = para.findNext('p').findNext('p').get_text()
                send_time = failed_details_msg.date
                failed_subject = failed_details_msg.subject
                # TODO: implement this so that adding other attrs is easier in the future
                err_details = {'email_of_err': email_of_err, 'err_reason': err_reason,
                               'send_time': send_time, 'failed_subject': failed_subject}
                # print(f"Email of err: {email_of_err},\nErr reason: {err_reason}\nSend time: {send_time}")
                return email_of_err, err_reason, send_time
        return None, None, None

    def _process_failed_msg(self, post_master_msg):
        try:
            self._ValidateResponseMsg(post_master_msg)
        except AttributeError as e:
            self._logger.warning("err: skipping this message")
            return e, None, None
        # FIXME: make this a generic filter or something when adding it to PyEmailerAJM
        if self._failed_msg_is_dam_eap_and_recent(post_master_msg):
            attachment_msg = self._fetch_failed_msg_details(post_master_msg)
            if isinstance(attachment_msg, Exception):
                return attachment_msg, None, None
            else:
                return self._process_failed_details_msg(attachment_msg)
        return None, None, None