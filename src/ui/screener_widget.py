from __future__ import annotations

from PySide6.QtCore import QItemSelection, Qt, Signal
from PySide6.QtWidgets import QHeaderView, QTableView, QVBoxLayout, QWidget

from src.ui.company_table_model import CompanyTableModel, ScreenerRow

_MIN_COLUMN_WIDTH = 80
_STRETCH_COLUMN = 1  # "Nom" stretches to fill remaining space


class ScreenerWidget(QWidget):
    row_selected = Signal(ScreenerRow)
    selection_cleared = Signal()

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

        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self._table)

    def _on_selection_changed(self, selected: QItemSelection, _deselected: QItemSelection) -> None:
        indexes = selected.indexes()
        if not indexes:
            self.selection_cleared.emit()
            return
        row_index = indexes[0].row()
        rows = self._model.rows()
        if 0 <= row_index < len(rows):
            self.row_selected.emit(rows[row_index])

    def rows(self) -> list[ScreenerRow]:
        return self._model.rows()

    def load(self, rows: list[ScreenerRow]) -> None:
        self._model.load(rows)
