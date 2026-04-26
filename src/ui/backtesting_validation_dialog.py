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

from src.services.backtesting_service import BacktestAnalysisResult

_NA = "—"
_SNAPSHOT_HEADERS = [
    "Snapshot date",
    "Scored",
    "Valid returns",
    "Benchmark",
    "Top 20%",
    "Middle",
    "Bottom 20%",
    "Top - Bottom",
]
_BUCKET_HEADERS = [
    "Bucket",
    "Valid returns",
    "Average return",
    "Median return",
    "Excess vs benchmark",
]


class BacktestingValidationDialog(QDialog):
    def __init__(self, analysis: BacktestAnalysisResult, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._analysis = analysis
        self.setWindowTitle("Backtesting ranking validation")
        self.resize(980, 620)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        summary = QLabel(_summary_text(self._analysis))
        summary.setWordWrap(True)
        summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(summary)

        tabs = QTabWidget()
        tabs.addTab(self._build_snapshots_table(), "Snapshots")
        tabs.addTab(self._build_bucket_table(), "Buckets")
        layout.addWidget(tabs)

    def _build_snapshots_table(self) -> QWidget:
        table = _base_table(len(self._analysis.snapshot_results), len(_SNAPSHOT_HEADERS), _SNAPSHOT_HEADERS)
        for row_index, result in enumerate(self._analysis.snapshot_results):
            _set_cell(table, row_index, 0, result.snapshot_date.isoformat())
            _set_cell(table, row_index, 1, str(result.scored_company_count), right=True)
            _set_cell(table, row_index, 2, str(result.valid_forward_returns), right=True)
            _set_cell(table, row_index, 3, _fmt_pct(result.benchmark_return), right=True)
            _set_cell(table, row_index, 4, _fmt_pct(result.top_bucket.average_return), right=True)
            _set_cell(table, row_index, 5, _fmt_pct(result.middle_bucket.average_return), right=True)
            _set_cell(table, row_index, 6, _fmt_pct(result.bottom_bucket.average_return), right=True)
            _set_cell(table, row_index, 7, _fmt_signed_pct(result.top_minus_bottom), right=True)
        container = QWidget()
        inner = QHBoxLayout(container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(table)
        return container

    def _build_bucket_table(self) -> QWidget:
        table = _base_table(len(self._analysis.bucket_summaries), len(_BUCKET_HEADERS), _BUCKET_HEADERS)
        for row_index, summary in enumerate(self._analysis.bucket_summaries):
            _set_cell(table, row_index, 0, summary.bucket)
            _set_cell(table, row_index, 1, str(summary.valid_returns), right=True)
            _set_cell(table, row_index, 2, _fmt_pct(summary.average_return), right=True)
            _set_cell(table, row_index, 3, _fmt_pct(summary.median_return), right=True)
            _set_cell(table, row_index, 4, _fmt_signed_pct(summary.average_excess_vs_benchmark), right=True)
        container = QWidget()
        inner = QHBoxLayout(container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(table)
        return container


def _summary_text(analysis: BacktestAnalysisResult) -> str:
    return (
        f"Benchmark: {analysis.benchmark_name} | "
        f"Forward horizon: {analysis.forward_days} days | "
        f"Snapshots: {analysis.total_snapshots} (evaluated: {analysis.evaluated_snapshots})\n"
        f"Ranking usefulness (top-bottom): {_fmt_signed_pct(analysis.ranking_usefulness)} | "
        f"Hit rate: {_fmt_pct(analysis.hit_rate)} | "
        f"Top excess vs benchmark: {_fmt_signed_pct(analysis.top_excess_vs_benchmark)} | "
        f"Score validation: {analysis.score_validation}"
    )


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


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return _NA
    return f"{value * 100:.2f}%"


def _fmt_signed_pct(value: float | None) -> str:
    if value is None:
        return _NA
    return f"{value * 100:+.2f}%"
