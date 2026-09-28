from typing import Optional

# noinspection PyUnresolvedReferences
from pywintypes import com_error


class EmailerNotSetupError(Exception):
    ...


class DisplayManualQuit(Exception):
    ...


class InvalidAlertLevel(Exception):
    DEFAULT_ERR_MSG = 'Invalid alert level: {}'

    def __init__(self, msg: '_AlertMessageBase', **kwargs):
        self.msg = msg
        self.err_msg_str = kwargs.get('err_msg_str', self.DEFAULT_ERR_MSG.format(self.msg.ALERT_LEVEL))
        super().__init__(self.err_msg_str)


class NoMessagesFetched(Exception):
    ...


class UnrecognizedEmailError(com_error):
    def __init__(self, err_msg: Optional[str] = None, **kwargs):
        self.err_msg = err_msg
        super().__init__(self.err_msg, **kwargs)


class RPCDownError(com_error):
    def __init__(self, err_msg: Optional[str] = None, sleep_time=-1, **kwargs):
        self.err_msg = err_msg
        self.sleep_time = sleep_time
        if not self.err_msg:
            self.err_msg = f"The RPC server is unavailable. Retrying in {self.sleep_time} seconds"
        super().__init__(self.err_msg, **kwargs)