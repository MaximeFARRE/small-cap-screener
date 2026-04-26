from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.services.screening_service import (
    ScreeningSnapshotComparisonRow,
    ScreeningSnapshotView,
)

_RESULT_HEADERS = [
    "Ticker",
    "Nom",
    "Secteur",
    "Score total",
    "Rang",
    "Rang secteur",
]
_COMPARISON_HEADERS = [
    "Ticker",
    "Nom",
    "Rang snapshot",
    "Rang actuel",
    "Delta rank",
    "Score snapshot",
    "Score actuel",
    "Delta score",
]
_NA = "—"


class ScreeningSnapshotDialog(QDialog):
    def __init__(
        self,
        snapshot_view: ScreeningSnapshotView,
        comparison_rows: list[ScreeningSnapshotComparisonRow],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._snapshot_view = snapshot_view
        self._comparison_rows = comparison_rows
        self.setWindowTitle(f"Snapshot screening #{snapshot_view.summary.snapshot_id}")
        self.resize(980, 640)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel(
            f"{self._snapshot_view.summary.name} | {self._snapshot_view.summary.created_at:%Y-%m-%d %H:%M} | "
            f"{self._snapshot_view.summary.company_count} société(s)"
        )
        title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(title)

        filters = QLabel(f"Filtres: {self._snapshot_view.summary.filters_summary}")
        filters.setWordWrap(True)
        filters.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(filters)

        tabs = QTabWidget()
        tabs.addTab(self._build_results_table(), "Résultats sauvegardés")
        tabs.addTab(self._build_comparison_table(), "Comparaison vs actuel")
        layout.addWidget(tabs)

    def _build_results_table(self) -> QWidget:
        table = _base_table(len(self._snapshot_view.rows), len(_RESULT_HEADERS), _RESULT_HEADERS)
        for row_index, row in enumerate(self._snapshot_view.rows):
            _set_cell(table, row_index, 0, row.ticker or _NA)
            _set_cell(table, row_index, 1, row.name)
            _set_cell(table, row_index, 2, row.sector or _NA)
            _set_cell(table, row_index, 3, _fmt_score(row.total_score), right=True)
            _set_cell(table, row_index, 4, _fmt_int(row.rank), right=True)
            _set_cell(table, row_index, 5, _fmt_int(row.sector_rank), right=True)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(table)
        return container

    def _build_comparison_table(self) -> QWidget:
        table = _base_table(len(self._comparison_rows), len(_COMPARISON_HEADERS), _COMPARISON_HEADERS)
        for row_index, row in enumerate(self._comparison_rows):
            _set_cell(table, row_index, 0, row.ticker or _NA)
            _set_cell(table, row_index, 1, row.name)
            _set_cell(table, row_index, 2, _fmt_int(row.snapshot_rank), right=True)
            _set_cell(table, row_index, 3, _fmt_int(row.current_rank), right=True)
            _set_cell(table, row_index, 4, _fmt_signed_int(row.rank_change), right=True)
            _set_cell(table, row_index, 5, _fmt_score(row.snapshot_total_score), right=True)
            _set_cell(table, row_index, 6, _fmt_score(row.current_total_score), right=True)
            _set_cell(table, row_index, 7, _fmt_signed_score(row.total_score_change), right=True)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(table)
        return container


def _base_table(row_count: int, column_count: int, headers: list[str]) -> QTableWidget:
    table = QTableWidget(row_count, column_count)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    table.verticalHeader().setVisible(False)
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setStretchLastSection(True)
    return table


def _set_cell(table: QTableWidget, row: int, column: int, text: str, *, right: bool = False) -> None:
    item = QTableWidgetItem(text)
    if right:
        item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
    table.setItem(row, column, item)


def _fmt_score(value: float | None) -> str:
    if value is None:
        return _NA
    return f"{value:.2f}"


def _fmt_signed_score(value: float | None) -> str:
    if value is None:
        return _NA
    return f"{value:+.2f}"


def _fmt_int(value: int | None) -> str:
    if value is None:
        return _NA
    return str(value)


def _fmt_signed_int(value: int | None) -> str:
    if value is None:
        return _NA
    return f"{value:+d}"
