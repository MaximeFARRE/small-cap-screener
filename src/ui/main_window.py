from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

WINDOW_TITLE = "Small Cap Screener"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self._setup_central_widget()

    def _setup_central_widget(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        placeholder = QLabel("Small Cap Screener — UI coming soon")
        layout.addWidget(placeholder)
