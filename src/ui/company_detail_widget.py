from __future__ import annotations

import math
from datetime import UTC, datetime

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QDateTimeAxis,
    QLineSeries,
    QValueAxis,
)
from PySide6.QtCore import QDateTime, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.models.watchlist_entry import (
    WATCHLIST_STATUS_CONVICTION,
    WATCHLIST_STATUS_REJECTED,
    WATCHLIST_STATUS_REVIEW,
    WATCHLIST_STATUS_WATCHING,
)
from src.services.company_charts_service import (
    CompanyChartsData,
    DatedChartPoint,
    ScoreBreakdownPoint,
    YearlyChartPoint,
)
from src.services.company_detail_service import CompanyFinancialDetail
from src.services.peer_comparison_service import PeerCompanyRow, PeerComparisonData, PeerMetricComparison
from src.services.scoring_service import ScoreExplanation, ScoreMetricDriver
from src.services.screening_service import STALE_REFRESH_DAYS
from src.services.watchlist_service import AnalystMemo, CompanyAnalystDetail
from src.ui.company_table_model import ScreenerRow

_NA = "N/A"
_PLACEHOLDER = "Sélectionnez une société"
_NOT_IN_WATCHLIST = "hors watchlist"
_DATA_QUALITY_HIGH = 0.8
_DATA_QUALITY_MEDIUM = 0.5
_ALERT_STYLE = "QFrame { background: #FFF3CD; border: 1px solid #FFC107; border-radius: 4px; padding: 4px; }"
_WATCHLIST_STATUS_OPTIONS: list[tuple[str, str]] = [
    ("watching", WATCHLIST_STATUS_WATCHING),
    ("review", WATCHLIST_STATUS_REVIEW),
    ("rejected", WATCHLIST_STATUS_REJECTED),
    ("conviction", WATCHLIST_STATUS_CONVICTION),
]

_GROUPS_ORDER = [
    "Société",
    "Financial overview",
    "Historical fundamentals",
    "Valuation ratios",
    "Quality / Growth / Risk",
    "Peer Comparison",
    "Analyste",
    "Analyst Memo",
    "Scoring",
]
_TREND_LABELS = {
    "positive": "positive",
    "negative": "negative",
    "stable": "stable",
}
_CHART_HEIGHT = 200
_PRICE_COLOR = "#1f77b4"
_REVENUE_COLOR = "#2ca02c"
_OPERATING_COLOR = "#ff7f0e"
_MARGIN_COLOR = "#d62728"
_SCORE_BAR_COLOR = "#4c78a8"
_NO_DATA_SUFFIX = " (no data)"


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
    save_watchlist_requested = Signal(int, str, str, bool, str, str, str, str, str, str)
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

        self._alert_frame = QFrame()
        self._alert_frame.setStyleSheet(_ALERT_STYLE)
        alert_layout = QVBoxLayout(self._alert_frame)
        alert_layout.setContentsMargins(6, 4, 6, 4)
        self._alert_label = QLabel()
        self._alert_label.setWordWrap(True)
        alert_layout.addWidget(self._alert_label)
        self._alert_frame.setVisible(False)
        outer_layout.addWidget(self._alert_frame)

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

        charts_box = QGroupBox("Visual analysis")
        charts_layout = QVBoxLayout(charts_box)
        self._price_chart_view = _build_chart_view()
        self._fundamentals_chart_view = _build_chart_view()
        self._margin_chart_view = _build_chart_view()
        self._score_chart_view = _build_chart_view()
        charts_layout.addWidget(self._price_chart_view)
        charts_layout.addWidget(self._fundamentals_chart_view)
        charts_layout.addWidget(self._margin_chart_view)
        charts_layout.addWidget(self._score_chart_view)
        self._content_layout.addWidget(charts_box)
        self._clear_charts()

        actions_box = QGroupBox("Actions analyste")
        actions_layout = QVBoxLayout(actions_box)
        actions_form = QFormLayout()

        self._status_input = QComboBox()
        for label, value in _WATCHLIST_STATUS_OPTIONS:
            self._status_input.addItem(label, value)

        self._notes_input = QLineEdit()
        self._excluded_input = QCheckBox("Exclure du screening")
        self._next_review_input = QLineEdit()
        self._next_review_input.setPlaceholderText("YYYY-MM-DD or YYYY-MM-DD HH:MM")
        self._investment_thesis_input = QTextEdit()
        self._key_risks_input = QTextEdit()
        self._catalysts_input = QTextEdit()
        self._valuation_notes_input = QTextEdit()
        self._next_action_input = QTextEdit()

        for widget in (
            self._investment_thesis_input,
            self._key_risks_input,
            self._catalysts_input,
            self._valuation_notes_input,
            self._next_action_input,
        ):
            widget.setMaximumHeight(70)

        actions_form.addRow("Status", self._status_input)
        actions_form.addRow("Notes", self._notes_input)
        actions_form.addRow("", self._excluded_input)
        actions_form.addRow("Next review at", self._next_review_input)
        actions_form.addRow("Investment thesis", self._investment_thesis_input)
        actions_form.addRow("Key risks", self._key_risks_input)
        actions_form.addRow("Catalysts", self._catalysts_input)
        actions_form.addRow("Valuation notes", self._valuation_notes_input)
        actions_form.addRow("Next action", self._next_action_input)
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
        chart_data: CompanyChartsData | None = None,
        peer_comparison: PeerComparisonData | None = None,
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
        score_explanation: ScoreExplanation | None = None
        analyst_memo = AnalystMemo()

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
            score_explanation = analyst_detail.score_explanation
            analyst_memo = analyst_detail.analyst_memo
            explanation_summary = analyst_detail.score_explanation.summary
            self._set_editor_values(
                status=analyst_detail.watchlist_status or WATCHLIST_STATUS_WATCHING,
                notes=analyst_detail.watchlist_notes or "",
                is_excluded=analyst_detail.watchlist_is_excluded,
                next_review_at=analyst_detail.next_review_at,
                memo=analyst_detail.analyst_memo,
            )
        else:
            self._in_watchlist = False
            self._set_editor_values(
                status=WATCHLIST_STATUS_WATCHING,
                notes="",
                is_excluded=False,
                next_review_at=None,
                memo=AnalystMemo(),
            )

        self._set_field("Société", "Nom", row.name)
        self._set_field("Société", "Ticker", row.ticker or _NA)
        self._set_field("Société", "Secteur", row.sector or _NA)
        self._set_field("Société", "Dernière actualisation", _fmt_refresh_date(row.last_universe_refresh_at))
        self._set_field(
            "Société",
            "Snapshot KPI",
            str(row.snapshot_date) if row.snapshot_date is not None else "Aucun",
        )

        self._populate_financial_overview(financial_detail, row.data_quality_score)
        self._populate_historical_fundamentals(financial_detail)
        self._populate_valuation_ratios(financial_detail)
        self._populate_quality_growth_risk(financial_detail)
        self._populate_charts(chart_data)
        self._populate_peer_comparison(peer_comparison)
        self._update_alerts(row)

        self._set_field("Analyste", "Status watchlist", watchlist_status)
        self._set_field("Analyste", "Notes watchlist", watchlist_notes)
        self._set_field("Analyste", "Exclue", "oui" if watchlist_is_excluded else "non")
        self._set_field(
            "Analyste", "Next review at", _fmt_next_review_at(analyst_detail.next_review_at if analyst_detail else None)
        )
        self._populate_analyst_memo(analyst_memo)
        self._set_field("Scoring", "Score total", _fmt(total_score))
        self._set_field("Scoring", "Quality", _fmt(quality_score))
        self._set_field("Scoring", "Value", _fmt(value_score))
        self._set_field("Scoring", "Growth", _fmt(growth_score))
        self._set_field("Scoring", "Risk", _fmt(risk_score))
        self._set_field("Scoring", "Rang global", str(rank) if rank is not None else _NA)
        self._set_field("Scoring", "Rang secteur", str(sector_rank) if sector_rank is not None else _NA)
        self._set_field("Scoring", "Poids actifs", _fmt_score_weights(score_explanation))
        self._set_field("Scoring", "Décomposition", _fmt_score_contributions(score_explanation))
        self._set_field("Scoring", "Drivers +", _fmt_score_drivers(score_explanation, positive=True))
        self._set_field("Scoring", "Drivers -", _fmt_score_drivers(score_explanation, positive=False))
        self._set_field("Scoring", "Forces", _fmt_score_points(score_explanation, strengths=True))
        self._set_field("Scoring", "Faiblesses", _fmt_score_points(score_explanation, strengths=False))
        self._set_field("Scoring", "Résumé score", explanation_summary)
        self._set_actions_enabled(True)
        self._add_watchlist_btn.setEnabled(not self._in_watchlist)
        self._remove_watchlist_btn.setEnabled(self._in_watchlist)

        self._placeholder.setVisible(False)
        self._scroll.setVisible(True)

    def _populate_financial_overview(
        self,
        detail: CompanyFinancialDetail | None,
        data_quality_score: float | None = None,
    ) -> None:
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
        fallback = detail.data_quality_score if detail else None
        score = data_quality_score if data_quality_score is not None else fallback
        self._set_field(
            "Financial overview",
            "Qualité données",
            _fmt_quality(score),
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

    def _populate_historical_fundamentals(self, detail: CompanyFinancialDetail | None) -> None:
        if detail is None:
            self._set_field("Historical fundamentals", "Revenue CAGR", _NA)
            self._set_field("Historical fundamentals", "Operating income CAGR", _NA)
            self._set_field("Historical fundamentals", "Net income CAGR", _NA)
            self._set_field("Historical fundamentals", "Free cash flow CAGR", _NA)
            self._set_field("Historical fundamentals", "Revenue trend", _NA)
            self._set_field("Historical fundamentals", "Margin trend", _NA)
            self._set_field("Historical fundamentals", "Net debt trend", _NA)
            self._set_field("Historical fundamentals", "Table", _NA)
            return

        trends = detail.historical_fundamentals.trends
        self._set_field("Historical fundamentals", "Revenue CAGR", _fmt_pct(trends.revenue_cagr))
        self._set_field("Historical fundamentals", "Operating income CAGR", _fmt_pct(trends.operating_income_cagr))
        self._set_field("Historical fundamentals", "Net income CAGR", _fmt_pct(trends.net_income_cagr))
        self._set_field("Historical fundamentals", "Free cash flow CAGR", _fmt_pct(trends.free_cash_flow_cagr))
        self._set_field("Historical fundamentals", "Revenue trend", _fmt_trend(trends.revenue_direction))
        self._set_field("Historical fundamentals", "Margin trend", _fmt_trend(trends.margin_direction))
        self._set_field("Historical fundamentals", "Net debt trend", _fmt_trend(trends.net_debt_direction))
        self._set_field("Historical fundamentals", "Table", _fmt_historical_table(detail))

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

    def _populate_charts(self, chart_data: CompanyChartsData | None) -> None:
        if chart_data is None:
            self._clear_charts()
            return
        self._price_chart_view.setChart(
            _line_chart_for_dated_points(
                title="Price history",
                points=chart_data.price_points,
                color=_PRICE_COLOR,
                y_title="Price",
            )
        )
        self._fundamentals_chart_view.setChart(
            _line_chart_for_year_points(
                title="Revenue and EBITDA / operating income",
                main_points=chart_data.fundamentals.revenue_points,
                main_label="Revenue",
                main_color=_REVENUE_COLOR,
                secondary_points=chart_data.fundamentals.operating_income_points,
                secondary_label="EBITDA / operating income",
                secondary_color=_OPERATING_COLOR,
                y_title="Amount",
            )
        )
        margin_points = [
            _to_year_point(point.fiscal_year, point.value * 100.0) for point in chart_data.fundamentals.margin_points
        ]
        self._margin_chart_view.setChart(
            _line_chart_for_year_points(
                title="Operating margin history (%)",
                main_points=margin_points,
                main_label="Margin %",
                main_color=_MARGIN_COLOR,
                secondary_points=[],
                secondary_label=None,
                secondary_color=None,
                y_title="Percent",
            )
        )
        self._score_chart_view.setChart(_score_breakdown_chart(chart_data.score_breakdown))

    def _clear_charts(self) -> None:
        self._price_chart_view.setChart(_empty_chart("Price history"))
        self._fundamentals_chart_view.setChart(_empty_chart("Revenue and EBITDA / operating income"))
        self._margin_chart_view.setChart(_empty_chart("Operating margin history (%)"))
        self._score_chart_view.setChart(_empty_chart("Score breakdown"))

    def _populate_peer_comparison(self, comparison: PeerComparisonData | None) -> None:
        if comparison is None:
            self._set_field("Peer Comparison", "Sector", _NA)
            self._set_field("Peer Comparison", "Relative rank", _NA)
            self._set_field("Peer Comparison", "Peer count", _NA)
            self._set_field("Peer Comparison", "Median comparison", _NA)
            self._set_field("Peer Comparison", "Peer table", _NA)
            return

        self._set_field("Peer Comparison", "Sector", comparison.sector or _NA)
        self._set_field(
            "Peer Comparison",
            "Relative rank",
            _fmt_relative_rank(comparison.company_sector_rank, comparison.sector_scored_count),
        )
        self._set_field("Peer Comparison", "Peer count", str(comparison.peer_count))
        self._set_field("Peer Comparison", "Median comparison", _fmt_peer_metric_comparisons(comparison.metrics))
        self._set_field("Peer Comparison", "Peer table", _fmt_peer_table(comparison.peer_rows))

    def _populate_analyst_memo(self, memo: AnalystMemo) -> None:
        self._set_field("Analyst Memo", "Investment thesis", _fmt_memo(memo.investment_thesis))
        self._set_field("Analyst Memo", "Key risks", _fmt_memo(memo.key_risks))
        self._set_field("Analyst Memo", "Catalysts", _fmt_memo(memo.catalysts))
        self._set_field("Analyst Memo", "Valuation notes", _fmt_memo(memo.valuation_notes))
        self._set_field("Analyst Memo", "Next action", _fmt_memo(memo.next_action))
        self._set_field("Analyst Memo", "Quick scan", _fmt_memo_quick_line(memo))

    def _update_alerts(self, row: ScreenerRow) -> None:
        alerts: list[str] = []
        if row.snapshot_date is None:
            alerts.append("Aucun snapshot KPI disponible.")
        if row.data_quality_score is None or row.data_quality_score < _DATA_QUALITY_MEDIUM:
            alerts.append("Qualité des données faible ou inconnue.")
        if row.last_universe_refresh_at is None:
            alerts.append("Données jamais actualisées.")
        else:
            now = datetime.now(UTC)
            refresh_at = row.last_universe_refresh_at
            if refresh_at.tzinfo is None:
                refresh_at = refresh_at.replace(tzinfo=UTC)
            age_days = (now - refresh_at).days
            if age_days > STALE_REFRESH_DAYS:
                alerts.append(f"Données obsolètes ({age_days} jours depuis la dernière actualisation).")
        if alerts:
            self._alert_label.setText("\n".join(alerts))
            self._alert_frame.setVisible(True)
        else:
            self._alert_frame.setVisible(False)

    def clear(self) -> None:
        self._current_row = None
        self._in_watchlist = False
        self._set_editor_values(
            status=WATCHLIST_STATUS_WATCHING,
            notes="",
            is_excluded=False,
            next_review_at=None,
            memo=AnalystMemo(),
        )
        self._set_actions_enabled(False)
        self._clear_charts()
        self._alert_frame.setVisible(False)
        self._scroll.setVisible(False)
        self._placeholder.setVisible(True)

    def _set_editor_values(
        self,
        *,
        status: str,
        notes: str,
        is_excluded: bool,
        next_review_at: datetime | None,
        memo: AnalystMemo,
    ) -> None:
        status_index = self._status_input.findData(status)
        if status_index < 0:
            status_index = self._status_input.findData(WATCHLIST_STATUS_WATCHING)
        if status_index >= 0:
            self._status_input.setCurrentIndex(status_index)
        self._notes_input.setText(notes)
        self._excluded_input.setChecked(is_excluded)
        self._next_review_input.setText(_to_next_review_editor_text(next_review_at))
        self._investment_thesis_input.setPlainText(memo.investment_thesis or "")
        self._key_risks_input.setPlainText(memo.key_risks or "")
        self._catalysts_input.setPlainText(memo.catalysts or "")
        self._valuation_notes_input.setPlainText(memo.valuation_notes or "")
        self._next_action_input.setPlainText(memo.next_action or "")

    def _set_actions_enabled(self, enabled: bool) -> None:
        self._status_input.setEnabled(enabled)
        self._notes_input.setEnabled(enabled)
        self._excluded_input.setEnabled(enabled)
        self._next_review_input.setEnabled(enabled)
        self._investment_thesis_input.setEnabled(enabled)
        self._key_risks_input.setEnabled(enabled)
        self._catalysts_input.setEnabled(enabled)
        self._valuation_notes_input.setEnabled(enabled)
        self._next_action_input.setEnabled(enabled)
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
            self._investment_thesis_input.toPlainText().strip(),
            self._key_risks_input.toPlainText().strip(),
            self._catalysts_input.toPlainText().strip(),
            self._valuation_notes_input.toPlainText().strip(),
            self._next_action_input.toPlainText().strip(),
            self._next_review_input.text().strip(),
        )

    def _on_refresh_clicked(self) -> None:
        if self._current_row is None:
            return
        self.refresh_company_requested.emit(self._current_row.company_id)


def _build_chart_view() -> QChartView:
    chart_view = QChartView()
    chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
    chart_view.setMinimumHeight(_CHART_HEIGHT)
    chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return chart_view


def _empty_chart(title: str) -> QChart:
    chart = QChart()
    chart.setTitle(title + _NO_DATA_SUFFIX)
    chart.legend().hide()
    return chart


def _line_chart_for_dated_points(
    *,
    title: str,
    points: list[DatedChartPoint],
    color: str,
    y_title: str,
) -> QChart:
    if not points:
        return _empty_chart(title)
    chart = QChart()
    chart.setTitle(title)
    chart.legend().hide()

    series = QLineSeries()
    series.setPen(_line_pen(color))
    chart.addSeries(series)

    values: list[float] = []
    for point in points:
        qdt = QDateTime(point.point_date.year, point.point_date.month, point.point_date.day, 0, 0)
        series.append(float(qdt.toMSecsSinceEpoch()), point.value)
        values.append(point.value)

    axis_x = QDateTimeAxis()
    axis_x.setFormat("yyyy-MM")
    axis_x.setTitleText("Date")
    start = QDateTime(points[0].point_date.year, points[0].point_date.month, points[0].point_date.day, 0, 0)
    end = QDateTime(points[-1].point_date.year, points[-1].point_date.month, points[-1].point_date.day, 0, 0)
    if len(points) == 1:
        start = start.addDays(-1)
        end = end.addDays(1)
    axis_x.setRange(start, end)
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    series.attachAxis(axis_x)

    axis_y = QValueAxis()
    axis_y.setLabelFormat("%.2f")
    axis_y.setTitleText(y_title)
    _set_value_axis_range(axis_y, min(values), max(values))
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_y)
    return chart


def _line_chart_for_year_points(
    *,
    title: str,
    main_points: list[YearlyChartPoint],
    main_label: str,
    main_color: str,
    secondary_points: list[YearlyChartPoint],
    secondary_label: str | None,
    secondary_color: str | None,
    y_title: str,
) -> QChart:
    has_main = bool(main_points)
    has_secondary = bool(secondary_points)
    if not has_main and not has_secondary:
        return _empty_chart(title)

    chart = QChart()
    chart.setTitle(title)
    chart.legend().setVisible(has_secondary)

    main_series = _year_line_series(main_label, main_points, main_color)
    chart.addSeries(main_series)
    all_points = list(main_points)

    secondary_series: QLineSeries | None = None
    if has_secondary and secondary_label is not None and secondary_color is not None:
        secondary_series = _year_line_series(secondary_label, secondary_points, secondary_color)
        chart.addSeries(secondary_series)
        all_points.extend(secondary_points)

    years = [point.fiscal_year for point in all_points]
    values = [point.value for point in all_points]

    axis_x = QValueAxis()
    axis_x.setLabelFormat("%.0f")
    axis_x.setTitleText("Fiscal year")
    _set_year_axis_range(axis_x, min(years), max(years))
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    main_series.attachAxis(axis_x)
    if secondary_series is not None:
        secondary_series.attachAxis(axis_x)

    axis_y = QValueAxis()
    axis_y.setLabelFormat("%.2f")
    axis_y.setTitleText(y_title)
    _set_value_axis_range(axis_y, min(values), max(values))
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    main_series.attachAxis(axis_y)
    if secondary_series is not None:
        secondary_series.attachAxis(axis_y)

    return chart


def _score_breakdown_chart(points: list[ScoreBreakdownPoint]) -> QChart:
    if not points:
        return _empty_chart("Score breakdown")

    chart = QChart()
    chart.setTitle("Score breakdown")
    chart.legend().hide()

    bar_set = QBarSet("Score")
    bar_set.setColor(QColor(_SCORE_BAR_COLOR))
    for point in points:
        bar_set.append(point.score)

    series = QBarSeries()
    series.append(bar_set)
    chart.addSeries(series)

    axis_x = QBarCategoryAxis()
    axis_x.append([point.label for point in points])
    axis_x.setTitleText("Category")
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    series.attachAxis(axis_x)

    max_score = max(100.0, max(point.score for point in points))
    axis_y = QValueAxis()
    axis_y.setLabelFormat("%.0f")
    axis_y.setTitleText("Score")
    axis_y.setRange(0.0, max_score * 1.05)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_y)
    return chart


def _line_pen(color: str) -> QPen:
    pen = QPen(QColor(color))
    pen.setWidth(2)
    return pen


def _year_line_series(name: str, points: list[YearlyChartPoint], color: str) -> QLineSeries:
    series = QLineSeries()
    series.setName(name)
    series.setPen(_line_pen(color))
    for point in points:
        series.append(float(point.fiscal_year), point.value)
    return series


def _set_year_axis_range(axis: QValueAxis, start_year: int, end_year: int) -> None:
    if start_year == end_year:
        axis.setRange(float(start_year - 1), float(end_year + 1))
        return
    axis.setRange(float(start_year), float(end_year))


def _set_value_axis_range(axis: QValueAxis, min_value: float, max_value: float) -> None:
    if min_value == max_value:
        padding = 1.0 if min_value == 0 else abs(min_value) * 0.1
        axis.setRange(min_value - padding, max_value + padding)
        return
    padding = abs(max_value - min_value) * 0.1
    axis.setRange(min_value - padding, max_value + padding)


def _to_year_point(fiscal_year: int, value: float) -> YearlyChartPoint:
    return YearlyChartPoint(fiscal_year=fiscal_year, value=value)


def _fmt_period(detail: CompanyFinancialDetail) -> str:
    if detail.fiscal_year is None:
        return _NA
    period_label = "annuel" if "annual" in (detail.period_type or "") else (detail.period_type or "")
    return f"{detail.fiscal_year} ({period_label})"


def _fmt_trend(value: str | None) -> str:
    if value is None:
        return _NA
    return _TREND_LABELS.get(value, value)


def _fmt_historical_table(detail: CompanyFinancialDetail) -> str:
    periods = [
        ("Revenues", detail.historical_fundamentals.revenue_history),
        ("Operating income", detail.historical_fundamentals.operating_income_history),
        ("Net income", detail.historical_fundamentals.net_income_history),
        ("Free cash flow", detail.historical_fundamentals.free_cash_flow_history),
        ("Net debt", detail.historical_fundamentals.net_debt_history),
    ]
    years = _collect_historical_years(periods)
    if not years:
        return _NA

    header = "Metric | " + " | ".join(str(year) for year in years)
    rows = [header]
    for label, history in periods:
        values = {point.fiscal_year: point for point in history}
        cells = [label]
        for year in years:
            point = values.get(year)
            cells.append(_fmt_history_cell(point.value, point.period_type, detail.currency) if point else _NA)
        rows.append(" | ".join(cells))
    return "<pre>" + "\n".join(rows) + "</pre>"


def _collect_historical_years(periods: list[tuple[str, list]]) -> list[int]:
    years: set[int] = set()
    for _, history in periods:
        for point in history:
            years.add(point.fiscal_year)
    return sorted(years, reverse=True)


def _fmt_history_cell(value: float | None, period_type: str | None, currency: str) -> str:
    if value is None:
        return _NA
    suffix = "A" if period_type and "annual" in period_type else "H"
    return f"{_fmt_large(value, currency)} ({suffix})"


def _fmt_quality(score: float | None) -> str:
    if score is None:
        return _NA
    pct = f"{score * 100:.1f}%"
    if score >= _DATA_QUALITY_HIGH:
        badge = "Élevée"
    elif score >= _DATA_QUALITY_MEDIUM:
        badge = "Moyenne"
    else:
        badge = "Faible"
    return f"{pct} ({badge})"


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _fmt_memo(value: str | None) -> str:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return _NA
    return "<pre>" + normalized + "</pre>"


def _fmt_memo_quick_line(memo: AnalystMemo) -> str:
    snippets = [
        _normalize_optional_text(memo.investment_thesis),
        _normalize_optional_text(memo.key_risks),
        _normalize_optional_text(memo.catalysts),
        _normalize_optional_text(memo.valuation_notes),
        _normalize_optional_text(memo.next_action),
    ]
    present = [item for item in snippets if item is not None]
    if not present:
        return _NA
    return " | ".join(present)


def _fmt_relative_rank(rank: int | None, sector_size: int) -> str:
    if rank is None or sector_size <= 0:
        return _NA
    return f"#{rank}/{sector_size} ({_relative_rank_signal(rank, sector_size)})"


def _relative_rank_signal(rank: int, sector_size: int) -> str:
    top_limit = max(1, math.ceil(sector_size / 3))
    mid_limit = max(top_limit, math.ceil((sector_size * 2) / 3))
    if rank <= top_limit:
        return "top tier"
    if rank <= mid_limit:
        return "mid tier"
    return "bottom tier"


def _fmt_peer_metric_comparisons(metrics: list[PeerMetricComparison]) -> str:
    if not metrics:
        return _NA
    lines = ["Metric | Company | Sector median | Position"]
    for metric in metrics:
        lines.append(
            " | ".join(
                [
                    metric.label,
                    _fmt_peer_metric_value(metric.key, metric.company_value),
                    _fmt_peer_metric_value(metric.key, metric.sector_median),
                    metric.position or _NA,
                ]
            )
        )
    return "<pre>" + "\n".join(lines) + "</pre>"


def _fmt_peer_table(rows: list[PeerCompanyRow]) -> str:
    if not rows:
        return _NA
    lines = ["Ticker | Rank | Score | EV/EBITDA | P/E | Op. margin | Rev. growth"]
    for row in rows:
        lines.append(
            " | ".join(
                [
                    row.ticker or _NA,
                    str(row.sector_rank) if row.sector_rank is not None else _NA,
                    _fmt_peer_metric_value("total_score", row.total_score),
                    _fmt_peer_metric_value("ev_ebitda", row.ev_ebitda),
                    _fmt_peer_metric_value("pe_ratio", row.pe_ratio),
                    _fmt_peer_metric_value("operating_margin", row.operating_margin),
                    _fmt_peer_metric_value("revenue_growth", row.revenue_growth),
                ]
            )
        )
    return "<pre>" + "\n".join(lines) + "</pre>"


def _fmt_peer_metric_value(metric_key: str, value: float | None) -> str:
    if metric_key in {"gross_margin", "operating_margin", "revenue_growth", "ebitda_growth"}:
        return _fmt_pct(value)
    if metric_key in {"ev_ebitda", "pe_ratio"}:
        return _fmt_ratio(value)
    if metric_key in {
        "total_score",
        "quality_score",
        "value_score",
        "growth_score",
        "risk_score",
        "data_quality_score",
    }:
        return _fmt(value, 1)
    return _fmt(value)


def _fmt_score_weights(explanation: ScoreExplanation | None) -> str:
    if explanation is None or not explanation.weights:
        return _NA
    return ", ".join(f"{entry.category} {entry.weight * 100:.1f}%" for entry in explanation.weights)


def _fmt_score_contributions(explanation: ScoreExplanation | None) -> str:
    if explanation is None or not explanation.category_contributions:
        return _NA
    rows = ["Category | Sub-score | Weight | Points"]
    for entry in explanation.category_contributions:
        rows.append(f"{entry.category} | {entry.sub_score:.2f} | {entry.weight:.2f} | {entry.weighted_points:.2f}")
    return "<pre>" + "\n".join(rows) + "</pre>"


def _fmt_score_drivers(explanation: ScoreExplanation | None, *, positive: bool) -> str:
    if explanation is None:
        return _NA
    drivers = explanation.positive_drivers if positive else explanation.negative_drivers
    if not drivers:
        return _NA
    return "<pre>" + "\n".join(_fmt_single_driver(driver) for driver in drivers) + "</pre>"


def _fmt_single_driver(driver: ScoreMetricDriver) -> str:
    return (
        f"{driver.category}.{driver.metric}: impact {driver.impact_points:+.2f} pts, "
        f"metric {driver.metric_score:.1f}/100, raw {driver.raw_value:.4g}"
    )


def _fmt_score_points(explanation: ScoreExplanation | None, *, strengths: bool) -> str:
    if explanation is None:
        return _NA
    points = explanation.strengths if strengths else explanation.weaknesses
    if not points:
        return _NA
    return "; ".join(points)


def _fmt_refresh_date(refresh_at: datetime | None) -> str:
    if refresh_at is None:
        return "Jamais"
    if refresh_at.tzinfo is None:
        refresh_at = refresh_at.replace(tzinfo=UTC)
    return refresh_at.strftime("%Y-%m-%d %H:%M")


def _fmt_next_review_at(next_review_at: datetime | None) -> str:
    if next_review_at is None:
        return _NA
    return _to_next_review_editor_text(next_review_at)


def _to_next_review_editor_text(next_review_at: datetime | None) -> str:
    if next_review_at is None:
        return ""
    if next_review_at.tzinfo is not None:
        next_review_at = next_review_at.astimezone(UTC)
    return next_review_at.strftime("%Y-%m-%d %H:%M")
