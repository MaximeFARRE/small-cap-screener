from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.models.watchlist_entry import (
    WATCHLIST_STATUS_CONVICTION,
    WATCHLIST_STATUS_REJECTED,
    WATCHLIST_STATUS_REVIEW,
    WATCHLIST_STATUS_WATCHING,
)
from src.services.company_detail_service import CompanyFinancialDetail
from src.services.watchlist_service import CompanyAnalystDetail
from src.ui.company_table_model import ScreenerRow

_NA = "N/A"
_PLACEHOLDER = "Sélectionnez une société"
_NOT_IN_WATCHLIST = "hors watchlist"
_WATCHLIST_STATUS_OPTIONS: list[tuple[str, str]] = [
    ("watching", WATCHLIST_STATUS_WATCHING),
    ("review", WATCHLIST_STATUS_REVIEW),
    ("rejected", WATCHLIST_STATUS_REJECTED),
    ("conviction", WATCHLIST_STATUS_CONVICTION),
]

_GROUPS_ORDER = [
    "Société",
    "Financial overview",
    "Valuation ratios",
    "Quality / Growth / Risk",
    "Analyste",
    "Scoring",
]


def _fmt(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return _NA
    return f"{value:.{decimals}f}"


def _fmt_pct(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return _NA
    return f"{value * 100:.{decimals}f}%"


def _fmt_large(value: float | None, currency: str = "EUR") -> str:
    """Format large monetary values as M or B with currency."""
    if value is None:
        return _NA
    abs_val = abs(value)
    if abs_val >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f} G{currency}"
    if abs_val >= 1_000_000:
        return f"{value / 1_000_000:.1f} M{currency}"
    return f"{value:,.0f} {currency}"


def _fmt_ratio(value: float | None, decimals: int = 1, suffix: str = "x") -> str:
    if value is None:
        return _NA
    return f"{value:.{decimals}f}{suffix}"


def _label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lbl


class CompanyDetailWidget(QWidget):
    add_watchlist_requested = Signal(int, str)
    remove_watchlist_requested = Signal(int)
    save_watchlist_requested = Signal(int, str, str, bool)
    refresh_company_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_row: ScreenerRow | None = None
        self._in_watchlist = False
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
        for title in _GROUPS_ORDER:
            box = QGroupBox(title)
            form = QFormLayout(box)
            self._groups[title] = form
            self._content_layout.addWidget(box)

        actions_box = QGroupBox("Actions analyste")
        actions_layout = QVBoxLayout(actions_box)
        actions_form = QFormLayout()

        self._status_input = QComboBox()
        for label, value in _WATCHLIST_STATUS_OPTIONS:
            self._status_input.addItem(label, value)

        self._notes_input = QLineEdit()
        self._excluded_input = QCheckBox("Exclure du screening")

        actions_form.addRow("Status", self._status_input)
        actions_form.addRow("Notes", self._notes_input)
        actions_form.addRow("", self._excluded_input)
        actions_layout.addLayout(actions_form)

        buttons_layout = QHBoxLayout()
        self._add_watchlist_btn = QPushButton("Ajouter watchlist")
        self._remove_watchlist_btn = QPushButton("Retirer watchlist")
        self._save_btn = QPushButton("Enregistrer")
        self._refresh_btn = QPushButton("Actualiser cette société")
        buttons_layout.addWidget(self._add_watchlist_btn)
        buttons_layout.addWidget(self._remove_watchlist_btn)
        buttons_layout.addWidget(self._save_btn)
        buttons_layout.addWidget(self._refresh_btn)
        actions_layout.addLayout(buttons_layout)
        self._content_layout.addWidget(actions_box)

        self._add_watchlist_btn.clicked.connect(self._on_add_watchlist_clicked)
        self._remove_watchlist_btn.clicked.connect(self._on_remove_watchlist_clicked)
        self._save_btn.clicked.connect(self._on_save_clicked)
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        self._set_actions_enabled(False)

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
        financial_detail: CompanyFinancialDetail | None = None,
    ) -> None:
        self._current_row = row
        for form in self._groups.values():
            while form.rowCount():
                form.removeRow(0)

        watchlist_status = _NOT_IN_WATCHLIST
        watchlist_notes = _NA
        watchlist_is_excluded = False
        total_score = row.total_score
        quality_score = row.quality_score
        value_score = row.value_score
        growth_score = row.growth_score
        risk_score = row.risk_score
        rank = row.rank
        sector_rank = row.sector_rank
        explanation_summary = _NA

        if analyst_detail is not None:
            self._in_watchlist = analyst_detail.watchlist_status is not None
            watchlist_status = analyst_detail.watchlist_status or _NOT_IN_WATCHLIST
            watchlist_notes = analyst_detail.watchlist_notes or _NA
            watchlist_is_excluded = analyst_detail.watchlist_is_excluded
            total_score = analyst_detail.total_score
            quality_score = analyst_detail.quality_score
            value_score = analyst_detail.value_score
            growth_score = analyst_detail.growth_score
            risk_score = analyst_detail.risk_score
            rank = analyst_detail.rank
            sector_rank = analyst_detail.sector_rank
            explanation_summary = analyst_detail.score_explanation.summary
            self._set_editor_values(
                status=analyst_detail.watchlist_status or WATCHLIST_STATUS_WATCHING,
                notes=analyst_detail.watchlist_notes or "",
                is_excluded=analyst_detail.watchlist_is_excluded,
            )
        else:
            self._in_watchlist = False
            self._set_editor_values(
                status=WATCHLIST_STATUS_WATCHING,
                notes="",
                is_excluded=False,
            )

        self._set_field("Société", "Nom", row.name)
        self._set_field("Société", "Ticker", row.ticker or _NA)
        self._set_field("Société", "Secteur", row.sector or _NA)

        self._populate_financial_overview(financial_detail)
        self._populate_valuation_ratios(financial_detail)
        self._populate_quality_growth_risk(financial_detail)

        self._set_field("Analyste", "Status watchlist", watchlist_status)
        self._set_field("Analyste", "Notes watchlist", watchlist_notes)
        self._set_field("Analyste", "Exclue", "oui" if watchlist_is_excluded else "non")
        self._set_field("Scoring", "Score total", _fmt(total_score))
        self._set_field("Scoring", "Quality", _fmt(quality_score))
        self._set_field("Scoring", "Value", _fmt(value_score))
        self._set_field("Scoring", "Growth", _fmt(growth_score))
        self._set_field("Scoring", "Risk", _fmt(risk_score))
        self._set_field("Scoring", "Rang global", str(rank) if rank is not None else _NA)
        self._set_field("Scoring", "Rang secteur", str(sector_rank) if sector_rank is not None else _NA)
        self._set_field("Scoring", "Résumé score", explanation_summary)
        self._set_actions_enabled(True)
        self._add_watchlist_btn.setEnabled(not self._in_watchlist)
        self._remove_watchlist_btn.setEnabled(self._in_watchlist)

        self._placeholder.setVisible(False)
        self._scroll.setVisible(True)

    def _populate_financial_overview(self, detail: CompanyFinancialDetail | None) -> None:
        ccy = detail.currency if detail is not None else "EUR"
        period = _fmt_period(detail) if detail is not None else _NA
        self._set_field("Financial overview", "Période", period)
        self._set_field(
            "Financial overview",
            "Prix actuel",
            _fmt(detail.current_price if detail else None, 2) + (f" {ccy}" if detail and detail.current_price else ""),
        )
        self._set_field(
            "Financial overview",
            "Market cap",
            _fmt_large(detail.market_cap if detail else None, ccy),
        )
        self._set_field(
            "Financial overview",
            "Enterprise value",
            _fmt_large(detail.enterprise_value if detail else None, ccy),
        )
        self._set_field(
            "Financial overview",
            "Revenus",
            _fmt_large(detail.revenue if detail else None, ccy),
        )
        self._set_field(
            "Financial overview",
            "EBITDA",
            _fmt_large(detail.ebitda if detail else None, ccy),
        )
        self._set_field(
            "Financial overview",
            "Résultat net",
            _fmt_large(detail.net_income if detail else None, ccy),
        )
        self._set_field(
            "Financial overview",
            "Free cash flow",
            _fmt_large(detail.free_cash_flow if detail else None, ccy),
        )
        self._set_field(
            "Financial overview",
            "Dette nette",
            _fmt_large(detail.net_debt if detail else None, ccy),
        )
        self._set_field(
            "Financial overview",
            "Qualité données",
            _fmt_pct(detail.data_quality_score if detail else None),
        )

    def _populate_valuation_ratios(self, detail: CompanyFinancialDetail | None) -> None:
        self._set_field(
            "Valuation ratios",
            "P/E",
            _fmt_ratio(detail.pe_ratio if detail else None),
        )
        self._set_field(
            "Valuation ratios",
            "P/B",
            _fmt_ratio(detail.pb_ratio if detail else None),
        )
        self._set_field(
            "Valuation ratios",
            "EV/EBITDA",
            _fmt_ratio(detail.ev_ebitda if detail else None),
        )
        self._set_field(
            "Valuation ratios",
            "EV/Sales",
            _fmt_ratio(detail.ev_sales if detail else None),
        )
        self._set_field(
            "Valuation ratios",
            "FCF yield",
            _fmt_pct(detail.fcf_yield if detail else None),
        )

    def _populate_quality_growth_risk(self, detail: CompanyFinancialDetail | None) -> None:
        self._set_field(
            "Quality / Growth / Risk",
            "Marge brute",
            _fmt_pct(detail.gross_margin if detail else None),
        )
        self._set_field(
            "Quality / Growth / Risk",
            "Marge opérationnelle",
            _fmt_pct(detail.operating_margin if detail else None),
        )
        self._set_field(
            "Quality / Growth / Risk",
            "Marge nette",
            _fmt_pct(detail.net_margin if detail else None),
        )
        self._set_field(
            "Quality / Growth / Risk",
            "ROE",
            _fmt_pct(detail.roe if detail else None),
        )
        self._set_field(
            "Quality / Growth / Risk",
            "ROIC",
            _fmt_pct(detail.roic if detail else None),
        )
        self._set_field(
            "Quality / Growth / Risk",
            "Croissance revenus",
            _fmt_pct(detail.revenue_growth if detail else None),
        )
        self._set_field(
            "Quality / Growth / Risk",
            "Croissance EBITDA",
            _fmt_pct(detail.ebitda_growth if detail else None),
        )
        self._set_field(
            "Quality / Growth / Risk",
            "Dette nette / EBITDA",
            _fmt_ratio(detail.net_debt_to_ebitda if detail else None),
        )

    def clear(self) -> None:
        self._current_row = None
        self._in_watchlist = False
        self._set_editor_values(
            status=WATCHLIST_STATUS_WATCHING,
            notes="",
            is_excluded=False,
        )
        self._set_actions_enabled(False)
        self._scroll.setVisible(False)
        self._placeholder.setVisible(True)

    def _set_editor_values(self, *, status: str, notes: str, is_excluded: bool) -> None:
        status_index = self._status_input.findData(status)
        if status_index < 0:
            status_index = self._status_input.findData(WATCHLIST_STATUS_WATCHING)
        if status_index >= 0:
            self._status_input.setCurrentIndex(status_index)
        self._notes_input.setText(notes)
        self._excluded_input.setChecked(is_excluded)

    def _set_actions_enabled(self, enabled: bool) -> None:
        self._status_input.setEnabled(enabled)
        self._notes_input.setEnabled(enabled)
        self._excluded_input.setEnabled(enabled)
        self._add_watchlist_btn.setEnabled(enabled)
        self._remove_watchlist_btn.setEnabled(enabled)
        self._save_btn.setEnabled(enabled)
        self._refresh_btn.setEnabled(enabled)

    def _on_add_watchlist_clicked(self) -> None:
        if self._current_row is None:
            return
        self.add_watchlist_requested.emit(self._current_row.company_id, self._notes_input.text().strip())

    def _on_remove_watchlist_clicked(self) -> None:
        if self._current_row is None:
            return
        self.remove_watchlist_requested.emit(self._current_row.company_id)

    def _on_save_clicked(self) -> None:
        if self._current_row is None:
            return
        status = str(self._status_input.currentData() or WATCHLIST_STATUS_WATCHING)
        notes = self._notes_input.text().strip()
        self.save_watchlist_requested.emit(
            self._current_row.company_id,
            status,
            notes,
            self._excluded_input.isChecked(),
        )

    def _on_refresh_clicked(self) -> None:
        if self._current_row is None:
            return
        self.refresh_company_requested.emit(self._current_row.company_id)


def _fmt_period(detail: CompanyFinancialDetail) -> str:
    if detail.fiscal_year is None:
        return _NA
    period_label = "annuel" if "annual" in (detail.period_type or "") else (detail.period_type or "")
    return f"{detail.fiscal_year} ({period_label})"
