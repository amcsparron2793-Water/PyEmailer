#! python3
"""
PyEmailer.py

install win32 with pip install pywin32
"""

# imports
import win32com.client as win32
from pythoncom import com_error
from logging import Logger
from CreateLogger import create_logger


class EmailerNotSetupError(Exception):
    ...


class PyEmailer:
    def __init__(self, display_window: bool,
                 send_emails: bool, logger: Logger = None,
                 auto_send: bool = False,
                 email_app_name: str = 'outlook.application'):

        if logger:
            self._logger = logger
        else:
            self._logger = Logger("DUMMY")
            print("Dummy logger in use!")

        self.email_app_name = email_app_name

        self.display_window = display_window
        self.auto_send = auto_send
        self.send_emails = send_emails
        self._setup_was_run = False

        self._recipient = None
        self._subject = None
        self._text = None

        try:
            self.email_app = win32.Dispatch(self.email_app_name)
            self.email = self.email_app.CreateItem(0)
        except com_error as e:
            self._logger.error(e, exc_info=True)
            raise e

    def SetupEmail(self, recipient: str, subject: str, text: str):
        try:
            # set the params
            self.email.To = recipient
            self.email.Subject = subject
            self.email.HtmlBody = text

            self._recipient = self.email.To
            self._subject = self.email.Subject
            self._text = self.email.HtmlBody

            print("New email set up successfully.")
            self._logger.info("New email set up successfully. see debug for details")
            self._logger.debug(f"Email recipient {recipient}, Subject {subject}, Message body {text}")
            self._setup_was_run = True
            return self.email

        except Exception as e:
            self._logger.error(e, exc_info=True)
            raise e

    def _display(self):
        print(f"Displaying the email in {self.email_app_name}, this window might open minimized.")
        logger.info(f"Displaying the email in {self.email_app_name}, this window might open minimized.")
        try:
            self.email.Display(True)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise e

    def _send(self):
        try:
            self.email.Send()
            print(f"Mail sent to {self._recipient}")
            logger.info(f"Mail successfully sent to {self._recipient}")
        except Exception as e:
            logger.error(e, exc_info=True)
            raise e

    def SendOrDisplay(self):
        if self._setup_was_run:
            print(f"Ready to send/display mail to/for {self._recipient}...")
            logger.info(f"Ready to send/display mail to/for {self._recipient}...")
            if self.send_emails and self.display_window:
                send_and_display_warning = ("Sending email while also displaying the email "
                                            "in the app is not possible. Defaulting to Display only")
                print(send_and_display_warning)
                self._logger.warning(send_and_display_warning)
                self.send_emails = False
                self.display_window = True

            if self.send_emails:
                if self.auto_send:
                    logger.info("Sending emails with auto_send...")
                    self._send()
                else:
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

            elif self.display_window:
                self._display()
            else:
                both_disabled_warning = ("Both sending and displaying the email are disabled. "
                                         "No errors were encountered.")
                self._logger.warning(both_disabled_warning)
                print(both_disabled_warning)
        else:
            try:
                raise EmailerNotSetupError("Setup has not been run, sending or displaying an email cannot occur.")
            except EmailerNotSetupError as e:
                logger.error(e, exc_info=True)
                raise e


if __name__ == "__main__":
    module_name = __file__.split('\\')[-1].split('.py')[0]
    logger = create_logger(project_name=module_name)

    emailer = PyEmailer(display_window=True, logger=logger, send_emails=True, auto_send=True)
    r_dict = {
        "recipient": "",
        "subject": "This is an auto generated email",
        "text": "&emsp; If your reading this, then it worked!"
    }
    # &emsp; is the tab character for emails
    emailer.SetupEmail(**r_dict)  # recipient="amcsparron@albanyny.gov", subject="test subject", text="test_body")
    emailer.SendOrDisplay()
