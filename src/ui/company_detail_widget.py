from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.services.watchlist_service import CompanyAnalystDetail
from src.ui.company_table_model import ScreenerRow

_NA = "—"
_PLACEHOLDER = "Sélectionnez une société"
_NOT_IN_WATCHLIST = "hors watchlist"


def _fmt(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return _NA
    return f"{value:.{decimals}f}"


def _label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lbl


class CompanyDetailWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        self._placeholder = QLabel(_PLACEHOLDER)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer_layout.addWidget(self._placeholder)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVisible(False)
        self._scroll = scroll
        outer_layout.addWidget(scroll)

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(content)

        self._groups: dict[str, QFormLayout] = {}
        for title in ("Société", "Analyste", "Scoring"):
            box = QGroupBox(title)
            form = QFormLayout(box)
            self._groups[title] = form
            self._content_layout.addWidget(box)

    def _set_field(self, group: str, label: str, value: str) -> None:
        form = self._groups[group]
        for i in range(form.rowCount()):
            item = form.itemAt(i, QFormLayout.ItemRole.LabelRole)
            if item and item.widget() and item.widget().text() == label:
                val_widget = form.itemAt(i, QFormLayout.ItemRole.FieldRole)
                if val_widget and val_widget.widget():
                    val_widget.widget().setText(value)
                return
        form.addRow(label, _label(value))

    def load(
        self,
        row: ScreenerRow,
        analyst_detail: CompanyAnalystDetail | None = None,
    ) -> None:
        for form in self._groups.values():
            while form.rowCount():
                form.removeRow(0)

        watchlist_status = _NOT_IN_WATCHLIST
        watchlist_notes = _NA
        quality_score = row.quality_score
        value_score = row.value_score
        growth_score = row.growth_score
        risk_score = row.risk_score
        explanation_summary = _NA

        if analyst_detail is not None:
            watchlist_status = analyst_detail.watchlist_status or _NOT_IN_WATCHLIST
            watchlist_notes = analyst_detail.watchlist_notes or _NA
            quality_score = analyst_detail.score_explanation.quality
            value_score = analyst_detail.score_explanation.value
            growth_score = analyst_detail.score_explanation.growth
            risk_score = analyst_detail.score_explanation.risk
            explanation_summary = analyst_detail.score_explanation.summary

        self._set_field("Société", "Nom", row.name)
        self._set_field("Société", "Ticker", row.ticker or _NA)
        self._set_field("Société", "Secteur", row.sector or _NA)
        self._set_field("Analyste", "Status watchlist", watchlist_status)
        self._set_field("Analyste", "Notes watchlist", watchlist_notes)
        self._set_field("Scoring", "Score total", _fmt(row.total_score))
        self._set_field("Scoring", "Quality", _fmt(quality_score))
        self._set_field("Scoring", "Value", _fmt(value_score))
        self._set_field("Scoring", "Growth", _fmt(growth_score))
        self._set_field("Scoring", "Risk", _fmt(risk_score))
        self._set_field("Scoring", "Rang global", str(row.rank) if row.rank is not None else _NA)
        self._set_field("Scoring", "Rang secteur", str(row.sector_rank) if row.sector_rank is not None else _NA)
        self._set_field("Scoring", "Résumé score", explanation_summary)

        self._placeholder.setVisible(False)
        self._scroll.setVisible(True)

    def clear(self) -> None:
        self._scroll.setVisible(False)
        self._placeholder.setVisible(True)
