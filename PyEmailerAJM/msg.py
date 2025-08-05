from os.path import isfile, isabs, abspath
import win32com.client as win32

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
