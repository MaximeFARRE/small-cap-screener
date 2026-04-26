import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.repositories.database import init_db
from src.ui.main_window import MainWindow


def _configure_runtime_workdir() -> None:
    if not getattr(sys, "frozen", False):
        return
    executable_dir = Path(sys.executable).resolve().parent
    if executable_dir.exists():
        os.chdir(executable_dir)


def run() -> None:
    _configure_runtime_workdir()
    init_db()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
