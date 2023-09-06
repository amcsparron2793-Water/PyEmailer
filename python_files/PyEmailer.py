# install with pip install pywin32
import win32com.client as win32
from pythoncom import com_error
from logging import Logger
from CreateLogger import create_logger


class PyEmailer:
    def __init__(self):
        pass


# this is for reference while I convert this into a class.
def emailer(text: str, subject: str, recipient: str, logger: Logger,
            Display: bool = True, Send: bool = False) -> None:
    try:
        # open outlook
        outlook = win32.Dispatch('outlook.application')
        # create a new email
        mail = outlook.CreateItem(0)
    except com_error as e:
        logger.error(e, exc_info=True)
        raise e
    try:
        # set the params
        mail.To = recipient
        mail.Subject = subject
        mail.HtmlBody = text

        print("New email set up successfully.")
        logger.info("New email set up successfully. see debug for details")
        logger.debug(f"Email recipient {recipient}, Subject {subject}, Message body {text}")
    except Exception as e:
        logger.error(e, exc_info=True)
        raise e

    # open the email as an outlook window
    if Display:
        print("Displaying the email in Outlook, this window might open minimized.")
        logger.info("Displaying the email in Outlook, this window might open minimized.")
        try:
            mail.Display(True)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise e

    # send the email using outlook
    if Send:
        print(f"Attempting to send mail to {recipient}...")
        logger.info(f"Attempting to send mail to {recipient}...")
        try:
            mail.Send()
            print(f"mail sent to {recipient}")
            logger.info(f"mail successfully sent to {recipient}")
        except Exception as e:
            logger.error(e, exc_info=True)
            raise e


if __name__ == "__main__":
    module_name = __file__.split('\\')[-1].split('.py')[0]
    logger = create_logger(project_name=module_name)
