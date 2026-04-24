from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableView, QVBoxLayout, QWidget

from src.ui.company_table_model import CompanyTableModel, ScreenerRow

_MIN_COLUMN_WIDTH = 80
_STRETCH_COLUMN = 0  # "Nom" stretches to fill remaining space


class ScreenerWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = CompanyTableModel()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._table.setSortingEnabled(False)
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(_STRETCH_COLUMN, QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(_MIN_COLUMN_WIDTH)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self._table)

    def load(self, rows: list[ScreenerRow]) -> None:
        self._model.load(rows)
