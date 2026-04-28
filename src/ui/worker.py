import inspect
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal


class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(Exception)
    progress = Signal(object)


class Worker(QThread):
    """
    A generic QThread-based worker to run blocking tasks in the background.
    Signals:
      - finished(object): emitted with the result of the function when complete.
      - error(Exception): emitted if the function raises an exception.
    """

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            call_kwargs = dict(self.kwargs)
            if _accepts_progress_callback(self.fn, call_kwargs):
                call_kwargs["progress_callback"] = self.signals.progress.emit
            result = self.fn(*self.args, **call_kwargs)
            self.signals.finished.emit(result)
        except Exception as exc:
            self.signals.error.emit(exc)


def _accepts_progress_callback(fn: Callable[..., Any], kwargs: dict[str, Any]) -> bool:
    if "progress_callback" in kwargs:
        return False
    signature = inspect.signature(fn)
    if "progress_callback" in signature.parameters:
        return True
    return any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values())
