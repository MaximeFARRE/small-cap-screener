from PySide6.QtWidgets import QMainWindow

from src.ui.screener_widget import ScreenerWidget

WINDOW_TITLE = "Small Cap Screener"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self._screener = ScreenerWidget()
        self.setCentralWidget(self._screener)
