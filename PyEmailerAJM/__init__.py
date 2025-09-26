from importlib import import_module


def is_instance_of_dynamic(obj: object, base_class_path: str) -> bool:
    """
    Check if an object is an instance of a class or its subclass specified by its module path.
    """
    try:
        module_path, class_name = base_class_path.rsplit('.', 1)
        module = import_module(module_path)
        base_class = getattr(module, class_name)
        return isinstance(obj, base_class)
    except (ImportError, AttributeError):
        return False


from PyEmailerAJM.backend import deprecated
from PyEmailerAJM.backend.errs import EmailerNotSetupError, DisplayManualQuit
from PyEmailerAJM.msg import Msg, FailedMsg
from PyEmailerAJM.searchers import BaseSearcher, SubjectSearcher
from PyEmailerAJM.py_emailer_ajm import PyEmailer, EmailerInitializer
from PyEmailerAJM.continuous_monitor.continuous_monitor import ContinuousMonitor

__all__ = ['EmailerNotSetupError', 'DisplayManualQuit', 'deprecated',
           'Msg', 'FailedMsg', 'PyEmailer', 'EmailerInitializer',
           'BaseSearcher', 'SubjectSearcher', 'ContinuousMonitor',
           'is_instance_of_dynamic']

