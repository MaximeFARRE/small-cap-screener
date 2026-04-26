from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal


class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(Exception)


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
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as exc:
            self.signals.error.emit(exc)
