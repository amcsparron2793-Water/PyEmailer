from pathlib import Path
# TODO: add these to other projects? and or EasyLogger?
__project_root__ = Path(__file__).parent.parent
__project_name__ = __project_root__.name
print(f'logs for {__project_name__} found in {__project_root__ / "logs"}')

from PyEmailerAJM.backend import deprecated
from PyEmailerAJM.backend.errs import EmailerNotSetupError, DisplayManualQuit
from PyEmailerAJM.msg import Msg, FailedMsg
from PyEmailerAJM.searchers import BaseSearcher, SubjectSearcher
from PyEmailerAJM.py_emailer_ajm import PyEmailer, EmailerInitializer
from PyEmailerAJM.continuous_monitor.continuous_monitor import ContinuousMonitor

__all__ = ['EmailerNotSetupError', 'DisplayManualQuit', 'deprecated',
           'Msg', 'FailedMsg', 'PyEmailer', 'EmailerInitializer',
           'BaseSearcher', 'SubjectSearcher', 'ContinuousMonitor',
           '__project_root__', '__project_name__']

