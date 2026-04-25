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

from src.ui.company_table_model import ScreenerRow

_NA = "—"
_PLACEHOLDER = "Sélectionnez une société"


def _fmt(value: float | None, pct: bool = False, decimals: int = 2) -> str:
    if value is None:
        return _NA
    if pct:
        return f"{value * 100:.{decimals}f} %"
    return f"{value:.{decimals}f}"


def _label(text: str) -> QLabel:
    lbl = QLabel(text)
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
        for title in ("Société", "Valorisation", "Rentabilité", "Levier", "Score"):
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

    def load(self, row: ScreenerRow) -> None:
        for form in self._groups.values():
            while form.rowCount():
                form.removeRow(0)

        r = row.ratios

        self._set_field("Société", "Nom", row.name)
        self._set_field("Société", "Ticker", row.ticker or _NA)
        self._set_field("Société", "Secteur", row.sector or _NA)
        self._set_field("Société", "Marché", row.market or _NA)
        self._set_field("Société", "Prix", _fmt(r.price))
        self._set_field("Société", "Année fiscale", str(r.fiscal_year))

        self._set_field("Valorisation", "Mkt Cap", _fmt(r.mkt_cap))
        self._set_field("Valorisation", "EV", _fmt(r.ev))
        self._set_field("Valorisation", "P/E", _fmt(r.pe_ratio))
        self._set_field("Valorisation", "P/B", _fmt(r.pb_ratio))
        self._set_field("Valorisation", "EV/EBITDA", _fmt(r.ev_ebitda))
        self._set_field("Valorisation", "EV/EBIT", _fmt(r.ev_ebit))
        self._set_field("Valorisation", "P/FCF", _fmt(r.price_to_fcf))

        self._set_field("Rentabilité", "ROE", _fmt(r.roe, pct=True))
        self._set_field("Rentabilité", "ROA", _fmt(r.roa, pct=True))
        self._set_field("Rentabilité", "Marge EBIT", _fmt(r.ebit_margin, pct=True))
        self._set_field("Rentabilité", "Marge EBITDA", _fmt(r.ebitda_margin, pct=True))
        self._set_field("Rentabilité", "Marge nette", _fmt(r.net_margin, pct=True))

        self._set_field("Levier", "Dette/CP", _fmt(r.debt_to_equity))
        self._set_field("Levier", "DN/EBITDA", _fmt(r.net_debt_to_ebitda))

        self._set_field("Score", "Score", f"{row.score:.1f} / 100")

        self._placeholder.setVisible(False)
        self._scroll.setVisible(True)

    def clear(self) -> None:
        self._scroll.setVisible(False)
        self._placeholder.setVisible(True)
