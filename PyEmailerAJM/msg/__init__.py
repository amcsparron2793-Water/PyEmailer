# pylint: disable=cyclic-import, wrong-import-position
from PyEmailerAJM.msg.msg import Msg, FailedMsg
from PyEmailerAJM.msg.factory import MsgFactory

__all__ = ['Msg', 'FailedMsg', 'MsgFactory']
