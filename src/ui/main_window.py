from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QSplitter

from src.ui.company_detail_widget import CompanyDetailWidget
from src.ui.screener_widget import ScreenerWidget

WINDOW_TITLE = "Small Cap Screener"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
_SPLITTER_RATIO = (2, 1)  # screener : detail


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self._setup_central_widget()

    def _setup_central_widget(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._screener = ScreenerWidget()
        self._detail = CompanyDetailWidget()

        splitter.addWidget(self._screener)
        splitter.addWidget(self._detail)
        splitter.setStretchFactor(0, _SPLITTER_RATIO[0])
        splitter.setStretchFactor(1, _SPLITTER_RATIO[1])

        self._screener.row_selected.connect(self._detail.load)
        self._screener.selection_cleared.connect(self._detail.clear)

        self.setCentralWidget(splitter)
