from __future__ import annotations

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
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
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
)
from src.services.company_detail_service import CompanyFinancialDetail
from src.services.peer_comparison_service import PeerComparisonData
from src.services.watchlist_service import CompanyAnalystDetail
from src.ui.company_table_model import ScreenerRow

# -- DESIGN SYSTEM FINANCE --
C_BG_MAIN = "#0F1115"
C_BG_CARD = "#171A21"
C_BG_SEC = "#1E222B"
C_BORDER = "#2A2F3A"
C_TEXT_MAIN = "#F3F4F6"
C_TEXT_SEC = "#AAB2BF"
C_POS = "#22C55E"
C_NEG = "#EF4444"
C_WARN = "#F59E0B"
C_ACC_PRI = "#3B82F6"
C_ACC_SEC = "#8B5CF6"

GLOBAL_STYLE = f"""
QWidget {{
    background-color: {C_BG_MAIN};
    color: {C_TEXT_MAIN};
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
}}
QScrollArea {{
    border: none;
    background-color: transparent;
}}
QFrame#Card {{
    background-color: {C_BG_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
}}
QLabel {{
    background-color: transparent;
}}
QLabel#HeroTitle {{
    font-size: 24px;
    font-weight: 700;
    color: {C_TEXT_MAIN};
}}
QLabel#HeroTicker {{
    font-size: 14px;
    font-weight: 600;
    color: {C_ACC_PRI};
    background-color: {C_BG_SEC};
    border: 1px solid {C_ACC_PRI};
    border-radius: 4px;
    padding: 2px 6px;
}}
QLabel#HeroSec {{
    font-size: 13px;
    color: {C_TEXT_SEC};
}}
QLabel#HeroPrice {{
    font-size: 28px;
    font-weight: 700;
    color: {C_TEXT_MAIN};
}}
QLabel#KpiValue {{
    font-size: 18px;
    font-weight: 600;
    font-family: 'IBM Plex Sans', 'JetBrains Mono', monospace;
}}
QLabel#KpiLabel {{
    font-size: 11px;
    font-weight: 600;
    color: {C_TEXT_SEC};
    text-transform: uppercase;
}}
QLabel#Badge {{
    font-size: 11px;
    font-weight: 600;
    border-radius: 4px;
    padding: 4px 8px;
}}
QPushButton {{
    background-color: {C_BG_SEC};
    color: {C_TEXT_MAIN};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {C_BORDER};
}}
QPushButton#PrimaryBtn {{
    background-color: {C_ACC_PRI};
    color: #FFFFFF;
    border: none;
}}
QPushButton#PrimaryBtn:hover {{
    background-color: #2563EB;
}}
QTableWidget {{
    background-color: {C_BG_CARD};
    color: {C_TEXT_MAIN};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    gridline-color: {C_BORDER};
    font-size: 12px;
}}
QHeaderView::section {{
    background-color: {C_BG_SEC};
    color: {C_TEXT_SEC};
    padding: 6px;
    border: none;
    border-bottom: 1px solid {C_BORDER};
    border-right: 1px solid {C_BORDER};
    font-weight: bold;
    font-size: 11px;
    text-transform: uppercase;
}}
QTableWidget::item {{
    padding: 6px;
    border-bottom: 1px solid {C_BORDER};
}}
QTabWidget::pane {{
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    background-color: {C_BG_MAIN};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {C_BG_SEC};
    color: {C_TEXT_SEC};
    padding: 8px 16px;
    border: 1px solid {C_BORDER};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background-color: {C_BG_CARD};
    color: {C_ACC_PRI};
}}
QTextEdit {{
    background-color: {C_BG_SEC};
    color: {C_TEXT_MAIN};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 6px;
    font-size: 12px;
}}
"""

_NA = "N/A"
_NOT_IN_WATCHLIST = "Not in watchlist"


def _fmt(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return _NA
    return f"{value:.{decimals}f}"


def _fmt_pct(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return _NA
    return f"{value * 100:.{decimals}f}%"


def _fmt_signed_pct(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return _NA
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def _to_quality_percent(value: float | None) -> float | None:
    if value is None:
        return None
    normalized = value * 100.0 if value <= 1.0 else value
    if normalized > 100.0:
        normalized = normalized / 100.0 if normalized <= 10_000.0 else 100.0
    if normalized < 0.0:
        return 0.0
    return min(normalized, 100.0)


def _fmt_quality_pct(value: float | None, decimals: int = 1) -> str:
    normalized = _to_quality_percent(value)
    if normalized is None:
        return _NA
    return f"{normalized:.{decimals}f}%"


def _fmt_ratio(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return _NA
    return f"{value:.{decimals}f}x"


def _fmt_bool(value: bool | None) -> str:
    if value is None:
        return _NA
    return "Yes" if value else "No"


def _fmt_large(value: float | None, currency: str = "EUR") -> str:
    if value is None:
        return _NA
    abs_val = abs(value)
    if abs_val >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f} B"
    if abs_val >= 1_000_000:
        return f"{value / 1_000_000:.1f} M"
    return f"{value:,.0f}"


def _get_signal_tuple(value: float, good_th: float, weak_th: float, gt_is_good: bool) -> tuple[str, str]:
    if gt_is_good:
        if value >= good_th:
            return "Good", C_POS
        if value < weak_th:
            return "Weak", C_NEG
        return "Neutral", C_WARN
    else:
        if value <= good_th:
            return "Good", C_POS
        if value > weak_th:
            return "Weak", C_NEG
        return "Neutral", C_WARN


def _kpi_signal(key: str, value: float | None) -> tuple[str, str]:
    if value is None:
        return "N/A", C_TEXT_SEC

    if key == "ROIC":
        return _get_signal_tuple(value, 0.10, 0.05, True)
    if key == "ROE":
        return _get_signal_tuple(value, 0.15, 0.05, True)
    if key == "Rev Growth":
        return _get_signal_tuple(value, 0.10, 0.00, True)
    if key == "Operating Margin":
        return _get_signal_tuple(value, 0.15, 0.05, True)
    if key == "Gross Margin":
        return _get_signal_tuple(value, 0.40, 0.20, True)
    if key == "FCF Yield":
        return _get_signal_tuple(value, 0.05, 0.00, True)
    if key == "Net Debt / EBITDA":
        return _get_signal_tuple(value, 2.0, 4.0, False)
    if key == "EV / EBITDA":
        return _get_signal_tuple(value, 10.0, 20.0, False)
    if key == "P/E":
        return _get_signal_tuple(value, 15.0, 30.0, False)

    return "Neutral", C_TEXT_SEC


def _create_badge(text: str, color: str, bg_color: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Badge")
    lbl.setStyleSheet(f"color: {color}; background-color: {bg_color}; border: 1px solid {color};")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


class CompanyDetailWidget(QWidget):
    add_watchlist_requested = Signal(int, str)
    remove_watchlist_requested = Signal(int)
    save_watchlist_requested = Signal(int, str, str, bool, str, str, str, str, str, str)
    refresh_company_requested = Signal(int)
    back_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_row: ScreenerRow | None = None
        self._in_watchlist = False
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(GLOBAL_STYLE)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Top Bar
        top_bar = QWidget()
        top_bar.setStyleSheet(f"background-color: {C_BG_SEC}; border-bottom: 1px solid {C_BORDER};")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 8, 16, 8)

        self._back_btn = QPushButton("← Back")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self.back_requested)
        top_layout.addWidget(self._back_btn)

        top_layout.addStretch()

        self._refresh_btn = QPushButton("Refresh Data")
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        top_layout.addWidget(self._refresh_btn)

        self._watchlist_btn = QPushButton("Add to Watchlist")
        self._watchlist_btn.setObjectName("PrimaryBtn")
        self._watchlist_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._watchlist_btn.clicked.connect(self._toggle_watchlist)
        top_layout.addWidget(self._watchlist_btn)

        self.main_layout.addWidget(top_bar)

        self._build_hero()
        self.main_layout.addWidget(self.hero_frame)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self._tab_snapshot = self._create_scroll_tab("Snapshot")
        self._tab_financials = self._create_scroll_tab("Financials")
        self._tab_peer = self._create_scroll_tab("Peer Comparison")
        self._tab_charts = self._create_scroll_tab("Charts")
        self._tab_ownership = self._create_scroll_tab("Ownership")
        self._tab_memo = self._create_scroll_tab("Memo / Thesis")
        self._tab_quality = self._create_scroll_tab("Data Quality")

        self._build_kpis(self._tab_snapshot)
        self._build_financials(self._tab_financials)
        self._build_peer_comparison(self._tab_peer)
        self._build_charts(self._tab_charts)
        self._build_ownership(self._tab_ownership)
        self._build_memo(self._tab_memo)
        self._build_quality(self._tab_quality)

    def _create_scroll_tab(self, name: str) -> QVBoxLayout:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(24)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, name)
        return content_layout

    def _build_hero(self) -> None:
        self.hero_frame = QFrame()
        self.hero_frame.setStyleSheet(f"background-color: {C_BG_MAIN}; border-bottom: 1px solid {C_BORDER};")
        hero_layout = QHBoxLayout(self.hero_frame)
        hero_layout.setContentsMargins(20, 20, 20, 20)

        # Left: Identity
        left_layout = QVBoxLayout()
        name_ticker_layout = QHBoxLayout()
        self.lbl_name = QLabel("COMPANY NAME")
        self.lbl_name.setObjectName("HeroTitle")
        self.lbl_ticker = QLabel("TICKER")
        self.lbl_ticker.setObjectName("HeroTicker")
        name_ticker_layout.addWidget(self.lbl_name)
        name_ticker_layout.addWidget(self.lbl_ticker)
        name_ticker_layout.addStretch()
        left_layout.addLayout(name_ticker_layout)

        self.lbl_sector = QLabel("Sector / Country / Exchange")
        self.lbl_sector.setObjectName("HeroSec")
        left_layout.addWidget(self.lbl_sector)
        hero_layout.addLayout(left_layout, stretch=2)

        # Mid: Valuation
        mid_layout = QVBoxLayout()
        self.lbl_price = QLabel("0.00 EUR")
        self.lbl_price.setObjectName("HeroPrice")
        mid_layout.addWidget(self.lbl_price)

        val_layout = QHBoxLayout()
        self.lbl_mcap = QLabel("MCap: -")
        self.lbl_mcap.setObjectName("HeroSec")
        self.lbl_ev_model = QLabel("EV (Model): -")
        self.lbl_ev_model.setObjectName("HeroSec")
        self.lbl_ev_yahoo = QLabel("EV (Yahoo): -")
        self.lbl_ev_yahoo.setObjectName("HeroSec")
        val_layout.addWidget(self.lbl_mcap)
        val_layout.addWidget(self.lbl_ev_model)
        val_layout.addWidget(self.lbl_ev_yahoo)
        val_layout.addStretch()
        mid_layout.addLayout(val_layout)
        hero_layout.addLayout(mid_layout, stretch=2)

        # Right: Signals/Badges
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        badges_top = QHBoxLayout()
        self.badge_score = _create_badge("Score: -", C_ACC_PRI, f"{C_ACC_PRI}20")
        self.badge_rank = _create_badge("Rank: -", C_TEXT_MAIN, C_BG_SEC)
        badges_top.addWidget(self.badge_score)
        badges_top.addWidget(self.badge_rank)
        badges_top.addStretch()
        right_layout.addLayout(badges_top)

        badges_bot = QHBoxLayout()
        self.badge_quality = _create_badge("Data: -", C_WARN, f"{C_WARN}20")
        self.badge_watchlist = _create_badge("Watchlist: -", C_TEXT_SEC, C_BG_SEC)
        badges_bot.addWidget(self.badge_quality)
        badges_bot.addWidget(self.badge_watchlist)
        badges_bot.addStretch()
        right_layout.addLayout(badges_bot)

        hero_meta = QGridLayout()
        hero_meta.setHorizontalSpacing(12)
        hero_meta.setVerticalSpacing(4)

        self.lbl_target = QLabel("Target: -")
        self.lbl_upside = QLabel("Upside/Downside: -")
        self.lbl_reco = QLabel("Reco: -")
        self.lbl_analyst_count = QLabel("Analysts: -")
        self.lbl_forward_pe = QLabel("Fwd P/E: -")
        self.lbl_beta = QLabel("Beta: -")
        self.lbl_confidence = QLabel("Confidence: -")
        self.lbl_last_refresh = QLabel("Last refresh: -")
        for label in (
            self.lbl_target,
            self.lbl_upside,
            self.lbl_reco,
            self.lbl_analyst_count,
            self.lbl_forward_pe,
            self.lbl_beta,
            self.lbl_confidence,
            self.lbl_last_refresh,
        ):
            label.setObjectName("HeroSec")

        hero_meta.addWidget(self.lbl_target, 0, 0)
        hero_meta.addWidget(self.lbl_upside, 0, 1)
        hero_meta.addWidget(self.lbl_reco, 1, 0)
        hero_meta.addWidget(self.lbl_analyst_count, 1, 1)
        hero_meta.addWidget(self.lbl_forward_pe, 2, 0)
        hero_meta.addWidget(self.lbl_beta, 2, 1)
        hero_meta.addWidget(self.lbl_confidence, 3, 0)
        hero_meta.addWidget(self.lbl_last_refresh, 3, 1)
        right_layout.addLayout(hero_meta)

        hero_layout.addLayout(right_layout, stretch=1)

    def _build_kpis(self, parent_layout: QVBoxLayout) -> None:
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(16)

        self.kpi_widgets = {}
        kpi_keys = [
            "Rev Growth",
            "Operating Margin",
            "Gross Margin",
            "ROIC",
            "ROE",
            "FCF Yield",
            "Net Debt / EBITDA",
            "EV / EBITDA",
            "P/E",
        ]

        for i, key in enumerate(kpi_keys):
            card = QFrame()
            card.setObjectName("Card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)

            lbl_title = QLabel(key)
            lbl_title.setObjectName("KpiLabel")

            val_layout = QHBoxLayout()
            lbl_val = QLabel("-")
            lbl_val.setObjectName("KpiValue")

            lbl_signal = _create_badge("-", C_TEXT_SEC, "transparent")
            lbl_signal.setStyleSheet(f"color: {C_TEXT_SEC}; font-weight: bold; font-size: 10px; border: none;")

            val_layout.addWidget(lbl_val)
            val_layout.addStretch()
            val_layout.addWidget(lbl_signal)

            card_layout.addWidget(lbl_title)
            card_layout.addLayout(val_layout)

            self.kpi_widgets[key] = (lbl_val, lbl_signal)
            self.kpi_grid.addWidget(card, i // 3, i % 3)

        parent_layout.addLayout(self.kpi_grid)
        self._build_profile_card(parent_layout)
        self._build_metrics_card(parent_layout)

    def _build_profile_card(self, parent_layout: QVBoxLayout) -> None:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        header = QLabel("Company Profile")
        header.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {C_TEXT_SEC};"
            f" text-transform: uppercase; padding-bottom: 4px;"
            f" border-bottom: 1px solid {C_BORDER};"
        )
        layout.addWidget(header)

        meta_layout = QGridLayout()
        meta_layout.setSpacing(8)
        meta_layout.setColumnMinimumWidth(1, 120)

        def _meta_label(text: str, bold: bool = False) -> QLabel:
            lbl = QLabel(text)
            style = f"color: {C_TEXT_SEC}; font-size: 12px;"
            if bold:
                style += f" font-weight: 600; color: {C_TEXT_MAIN};"
            lbl.setStyleSheet(style)
            lbl.setWordWrap(True)
            return lbl

        meta_layout.addWidget(_meta_label("Industry"), 0, 0)
        self._lbl_profile_industry = _meta_label("-", bold=True)
        meta_layout.addWidget(self._lbl_profile_industry, 0, 1)

        meta_layout.addWidget(_meta_label("Location"), 1, 0)
        self._lbl_profile_location = _meta_label("-", bold=True)
        meta_layout.addWidget(self._lbl_profile_location, 1, 1)

        meta_layout.addWidget(_meta_label("Employees"), 2, 0)
        self._lbl_profile_employees = _meta_label("-", bold=True)
        meta_layout.addWidget(self._lbl_profile_employees, 2, 1)

        meta_layout.addWidget(_meta_label("Website"), 3, 0)
        self._lbl_profile_website = QLabel("-")
        self._lbl_profile_website.setStyleSheet(f"color: {C_ACC_PRI}; font-size: 12px; font-weight: 600;")
        self._lbl_profile_website.setWordWrap(True)
        meta_layout.addWidget(self._lbl_profile_website, 3, 1)

        meta_layout.addWidget(_meta_label("Phone"), 4, 0)
        self._lbl_profile_phone = _meta_label("-", bold=True)
        meta_layout.addWidget(self._lbl_profile_phone, 4, 1)

        layout.addLayout(meta_layout)

        parent_layout.addWidget(frame)

    def _build_metrics_card(self, parent_layout: QVBoxLayout) -> None:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        header = QLabel("Key Metrics & Dividends")
        header.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {C_TEXT_SEC};"
            f" text-transform: uppercase; padding-bottom: 4px;"
            f" border-bottom: 1px solid {C_BORDER};"
        )
        layout.addWidget(header)

        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(12)

        def _meta_label(text: str, bold: bool = False, color: str = C_TEXT_MAIN) -> QLabel:
            lbl = QLabel(text)
            style = f"color: {C_TEXT_SEC}; font-size: 11px;"
            if bold:
                style += f" font-weight: 600; color: {color};"
            lbl.setStyleSheet(style)
            return lbl

        # Left Column: Margins & Returns
        metrics_layout.addWidget(_meta_label("Gross Margin"), 0, 0)
        self._lbl_gross_margin = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_gross_margin, 0, 1)

        metrics_layout.addWidget(_meta_label("Op. Margin"), 1, 0)
        self._lbl_op_margin = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_op_margin, 1, 1)

        metrics_layout.addWidget(_meta_label("Profit Margin"), 2, 0)
        self._lbl_profit_margin = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_profit_margin, 2, 1)

        metrics_layout.addWidget(_meta_label("ROE"), 3, 0)
        self._lbl_roe = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_roe, 3, 1)

        metrics_layout.addWidget(_meta_label("ROA"), 4, 0)
        self._lbl_roa = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_roa, 4, 1)

        # Middle Column: Analyst KPIs
        metrics_layout.addWidget(_meta_label("Current Ratio"), 0, 2)
        self._lbl_current_ratio = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_current_ratio, 0, 3)

        metrics_layout.addWidget(_meta_label("Quick Ratio"), 1, 2)
        self._lbl_quick_ratio = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_quick_ratio, 1, 3)

        metrics_layout.addWidget(_meta_label("Payout Ratio"), 2, 2)
        self._lbl_payout_ratio = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_payout_ratio, 2, 3)

        metrics_layout.addWidget(_meta_label("Avg. Volume"), 3, 2)
        self._lbl_avg_volume = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_avg_volume, 3, 3)

        metrics_layout.addWidget(_meta_label("Shares Out."), 4, 2)
        self._lbl_shares_outstanding = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_shares_outstanding, 4, 3)

        # Right Column: Targets & Dividends
        metrics_layout.addWidget(_meta_label("Div. Yield"), 0, 4)
        self._lbl_div_yield = _meta_label("-", bold=True, color=C_POS)
        metrics_layout.addWidget(self._lbl_div_yield, 0, 5)

        metrics_layout.addWidget(_meta_label("Target Upside"), 1, 4)
        self._lbl_target_upside = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_target_upside, 1, 5)

        metrics_layout.addWidget(_meta_label("Target Price"), 2, 4)
        self._lbl_target_price = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_target_price, 2, 5)

        metrics_layout.addWidget(_meta_label("Float Shares"), 3, 4)
        self._lbl_float_shares = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_float_shares, 3, 5)

        metrics_layout.addWidget(_meta_label("5Y Avg Yield"), 4, 4)
        self._lbl_5y_div_yield = _meta_label("-", bold=True)
        metrics_layout.addWidget(self._lbl_5y_div_yield, 4, 5)

        layout.addLayout(metrics_layout)
        parent_layout.addWidget(frame)

    def _build_financials(self, parent_layout: QVBoxLayout) -> None:
        fin_frame = QFrame()
        fin_frame.setObjectName("Card")
        fin_layout = QVBoxLayout(fin_frame)
        fin_layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Historical Financials")
        header.setStyleSheet(
            f"font-size: 14px; font-weight: bold; padding: 12px 16px; border-bottom: 1px solid {C_BORDER};"
        )
        fin_layout.addWidget(header)

        self.fin_table = QTableWidget()
        self.fin_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.fin_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.fin_table.verticalHeader().setVisible(False)
        self.fin_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fin_table.setFrameShape(QFrame.Shape.NoFrame)
        self.fin_table.setFixedHeight(350)
        fin_layout.addWidget(self.fin_table)

        parent_layout.addWidget(fin_frame)

    def _build_charts(self, parent_layout: QVBoxLayout) -> None:
        # We will dynamically recreate QChartViews later in populate to avoid memory leaks
        self.chart_container = QVBoxLayout()
        self.chart_container.setSpacing(24)
        parent_layout.addLayout(self.chart_container)

    def _build_ownership(self, parent_layout: QVBoxLayout) -> None:
        management_frame = QFrame()
        management_frame.setObjectName("Card")
        management_layout = QGridLayout(management_frame)
        management_layout.setContentsMargins(16, 12, 16, 16)
        management_layout.setHorizontalSpacing(16)
        management_layout.setVerticalSpacing(8)
        management_title = QLabel("Management")
        management_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        management_layout.addWidget(management_title, 0, 0, 1, 2)
        management_layout.addWidget(QLabel("CEO"), 1, 0)
        self._lbl_ceo = QLabel("-")
        management_layout.addWidget(self._lbl_ceo, 1, 1)
        management_layout.addWidget(QLabel("CFO"), 2, 0)
        self._lbl_cfo = QLabel("-")
        management_layout.addWidget(self._lbl_cfo, 2, 1)
        self._lbl_ownership_status = QLabel("")
        self._lbl_ownership_status.setStyleSheet(f"color: {C_TEXT_SEC};")
        management_layout.addWidget(self._lbl_ownership_status, 3, 0, 1, 2)
        parent_layout.addWidget(management_frame)

        holders_frame = QFrame()
        holders_frame.setObjectName("Card")
        holders_layout = QVBoxLayout(holders_frame)
        holders_layout.setContentsMargins(16, 12, 16, 16)
        holders_title = QLabel("Top Holders")
        holders_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        holders_layout.addWidget(holders_title)
        self._tbl_top_holders = QTableWidget()
        self._tbl_top_holders.setColumnCount(4)
        self._tbl_top_holders.setHorizontalHeaderLabels(["Holder", "Type", "Weight", "Reported"])
        self._tbl_top_holders.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tbl_top_holders.verticalHeader().setVisible(False)
        self._tbl_top_holders.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl_top_holders.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._tbl_top_holders.setFixedHeight(170)
        holders_layout.addWidget(self._tbl_top_holders)

        self._tbl_institutional_holders = QTableWidget()
        self._tbl_institutional_holders.setColumnCount(3)
        self._tbl_institutional_holders.setHorizontalHeaderLabels(["Institution", "Weight", "Reported"])
        self._tbl_institutional_holders.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tbl_institutional_holders.verticalHeader().setVisible(False)
        self._tbl_institutional_holders.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl_institutional_holders.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._tbl_institutional_holders.setFixedHeight(170)
        holders_layout.addWidget(self._tbl_institutional_holders)
        parent_layout.addWidget(holders_frame)

        insider_frame = QFrame()
        insider_frame.setObjectName("Card")
        insider_layout = QVBoxLayout(insider_frame)
        insider_layout.setContentsMargins(16, 12, 16, 16)
        insider_title = QLabel("Insider Activity")
        insider_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        insider_layout.addWidget(insider_title)
        self._tbl_insider_activity = QTableWidget()
        self._tbl_insider_activity.setColumnCount(4)
        self._tbl_insider_activity.setHorizontalHeaderLabels(["Insider", "Role", "Activity", "Date"])
        self._tbl_insider_activity.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tbl_insider_activity.verticalHeader().setVisible(False)
        self._tbl_insider_activity.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl_insider_activity.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._tbl_insider_activity.setFixedHeight(170)
        insider_layout.addWidget(self._tbl_insider_activity)
        parent_layout.addWidget(insider_frame)

    def _build_memo(self, parent_layout: QVBoxLayout) -> None:
        summary_frame = QFrame()
        summary_frame.setObjectName("Card")
        summary_layout = QVBoxLayout(summary_frame)
        summary_header = QLabel("Business Summary")
        summary_header.setStyleSheet("font-size: 14px; font-weight: bold; padding-bottom: 8px;")
        summary_layout.addWidget(summary_header)
        self._memo_business_summary = QTextEdit()
        self._memo_business_summary.setReadOnly(True)
        self._memo_business_summary.setMinimumHeight(90)
        self._memo_business_summary.setMaximumHeight(150)
        self._memo_business_summary.setPlaceholderText("No business summary available.")
        summary_layout.addWidget(self._memo_business_summary)
        parent_layout.addWidget(summary_frame)

        # Strengths & Weaknesses
        sw_layout = QHBoxLayout()

        self.str_frame = QFrame()
        self.str_frame.setObjectName("Card")
        str_layout = QVBoxLayout(self.str_frame)
        self.lbl_strengths = QLabel("Strengths")
        self.lbl_strengths.setStyleSheet(f"color: {C_POS}; font-weight: bold; font-size: 14px;")
        self.txt_strengths = QLabel("-")
        self.txt_strengths.setWordWrap(True)
        self.txt_strengths.setStyleSheet(f"color: {C_TEXT_MAIN}; line-height: 1.5;")
        str_layout.addWidget(self.lbl_strengths)
        str_layout.addWidget(self.txt_strengths)
        str_layout.addStretch()
        sw_layout.addWidget(self.str_frame)

        self.weak_frame = QFrame()
        self.weak_frame.setObjectName("Card")
        weak_layout = QVBoxLayout(self.weak_frame)
        self.lbl_weaknesses = QLabel("Weaknesses")
        self.lbl_weaknesses.setStyleSheet(f"color: {C_WARN}; font-weight: bold; font-size: 14px;")
        self.txt_weaknesses = QLabel("-")
        self.txt_weaknesses.setWordWrap(True)
        self.txt_weaknesses.setStyleSheet(f"color: {C_TEXT_MAIN}; line-height: 1.5;")
        weak_layout.addWidget(self.lbl_weaknesses)
        weak_layout.addWidget(self.txt_weaknesses)
        weak_layout.addStretch()
        sw_layout.addWidget(self.weak_frame)

        self.red_frame = QFrame()
        self.red_frame.setObjectName("Card")
        red_layout = QVBoxLayout(self.red_frame)
        self.lbl_red = QLabel("Red Flags")
        self.lbl_red.setStyleSheet(f"color: {C_NEG}; font-weight: bold; font-size: 14px;")
        self.txt_red = QLabel("-")
        self.txt_red.setWordWrap(True)
        self.txt_red.setStyleSheet(f"color: {C_TEXT_MAIN}; line-height: 1.5;")
        red_layout.addWidget(self.lbl_red)
        red_layout.addWidget(self.txt_red)
        red_layout.addStretch()
        sw_layout.addWidget(self.red_frame)

        parent_layout.addLayout(sw_layout)

        # Analyst Memo inputs (read-only style for now, or editable if they click edit)
        memo_frame = QFrame()
        memo_frame.setObjectName("Card")
        memo_layout = QVBoxLayout(memo_frame)
        memo_header = QLabel("Analyst Memo")
        memo_header.setStyleSheet("font-size: 14px; font-weight: bold; padding-bottom: 8px;")
        memo_layout.addWidget(memo_header)

        form_layout = QFormLayout()

        self.input_status = QComboBox()
        self.input_status.addItem("watching", WATCHLIST_STATUS_WATCHING)
        self.input_status.addItem("review", WATCHLIST_STATUS_REVIEW)
        self.input_status.addItem("rejected", WATCHLIST_STATUS_REJECTED)
        self.input_status.addItem("conviction", WATCHLIST_STATUS_CONVICTION)
        form_layout.addRow("Status", self.input_status)

        self.input_excluded = QCheckBox("Exclude from screening")
        form_layout.addRow("", self.input_excluded)

        self.input_notes = QLineEdit()
        form_layout.addRow("Notes", self.input_notes)

        self.input_review_at = QLineEdit()
        self.input_review_at.setPlaceholderText("YYYY-MM-DD or YYYY-MM-DD HH:MM")
        form_layout.addRow("Next review at", self.input_review_at)

        self.input_thesis = QTextEdit()
        self.input_thesis.setMaximumHeight(60)
        form_layout.addRow("Investment Thesis", self.input_thesis)

        self.input_risks = QTextEdit()
        self.input_risks.setMaximumHeight(60)
        form_layout.addRow("Key Risks", self.input_risks)

        self.input_catalysts = QTextEdit()
        self.input_catalysts.setMaximumHeight(60)
        form_layout.addRow("Catalysts", self.input_catalysts)

        self.input_val = QTextEdit()
        self.input_val.setMaximumHeight(60)
        form_layout.addRow("Valuation Notes", self.input_val)

        self.input_action = QTextEdit()
        self.input_action.setMaximumHeight(60)
        form_layout.addRow("Next Action", self.input_action)

        memo_layout.addLayout(form_layout)

        btn_save_memo = QPushButton("Save Analyst Data")
        btn_save_memo.setObjectName("PrimaryBtn")
        btn_save_memo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_memo.clicked.connect(self._on_save_clicked)
        memo_layout.addWidget(btn_save_memo, alignment=Qt.AlignmentFlag.AlignRight)

        parent_layout.addWidget(memo_frame)

    def _build_quality(self, parent_layout: QVBoxLayout) -> None:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QGridLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)

        self.lbl_q_score = QLabel("Data Quality: -")
        self.lbl_q_score.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.lbl_q_score, 0, 0, 1, 2)

        self.lbl_q_provider = QLabel("Provider: -")
        self.lbl_q_snapshot_source = QLabel("Snapshot source: -")
        self.lbl_q_refresh = QLabel("Last refresh: -")
        self.lbl_q_snapshot_date = QLabel("Snapshot date: -")
        self.lbl_q_confidence = QLabel("Confidence: -")
        for row_index, label in enumerate(
            (
                self.lbl_q_provider,
                self.lbl_q_snapshot_source,
                self.lbl_q_refresh,
                self.lbl_q_snapshot_date,
                self.lbl_q_confidence,
            ),
            start=1,
        ):
            label.setStyleSheet(f"color: {C_TEXT_MAIN};")
            layout.addWidget(label, row_index, 0, 1, 2)

        self.lbl_q_desc = QLabel("Missing fields: -")
        self.lbl_q_desc.setWordWrap(True)
        self.lbl_q_desc.setStyleSheet(f"color: {C_TEXT_SEC};")
        layout.addWidget(self.lbl_q_desc, 6, 0, 1, 2)

        parent_layout.addWidget(frame)

    def _build_peer_comparison(self, parent_layout: QVBoxLayout) -> None:
        summary_card = QFrame()
        summary_card.setObjectName("Card")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(16, 12, 16, 12)
        summary_layout.setSpacing(8)

        self._peer_summary_label = QLabel("Peer set: -")
        self._peer_summary_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        summary_layout.addWidget(self._peer_summary_label)

        self._peer_analyst_label = QLabel("Analyst view: -")
        self._peer_analyst_label.setWordWrap(True)
        self._peer_analyst_label.setStyleSheet(f"color: {C_TEXT_SEC};")
        summary_layout.addWidget(self._peer_analyst_label)
        parent_layout.addWidget(summary_card)

        metric_card = QFrame()
        metric_card.setObjectName("Card")
        metric_layout = QVBoxLayout(metric_card)
        metric_layout.setContentsMargins(16, 12, 16, 12)
        metric_layout.setSpacing(8)
        metric_title = QLabel("Peer metrics (company vs sector median)")
        metric_title.setStyleSheet("font-size: 12px; font-weight: 600;")
        metric_layout.addWidget(metric_title)

        self._peer_metric_table = QTableWidget()
        self._peer_metric_table.setColumnCount(5)
        self._peer_metric_table.setHorizontalHeaderLabels(
            ["Metric", "Company", "Sector Median", "Percentile", "Premium/Discount"]
        )
        self._peer_metric_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._peer_metric_table.verticalHeader().setVisible(False)
        metric_layout.addWidget(self._peer_metric_table)
        parent_layout.addWidget(metric_card)

        peers_card = QFrame()
        peers_card.setObjectName("Card")
        peers_layout = QVBoxLayout(peers_card)
        peers_layout.setContentsMargins(16, 12, 16, 12)
        peers_layout.setSpacing(8)
        peers_title = QLabel("Closest peers")
        peers_title.setStyleSheet("font-size: 12px; font-weight: 600;")
        peers_layout.addWidget(peers_title)

        self._peer_table = QTableWidget()
        self._peer_table.setColumnCount(10)
        self._peer_table.setHorizontalHeaderLabels(
            [
                "Ticker",
                "Name",
                "MCap",
                "EV/EBITDA",
                "P/E",
                "FCF Yield",
                "Rev Growth",
                "EBITDA Margin",
                "ROIC",
                "Net Debt/EBITDA",
            ]
        )
        self._peer_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._peer_table.verticalHeader().setVisible(False)
        peers_layout.addWidget(self._peer_table)
        parent_layout.addWidget(peers_card)

    def load(
        self,
        row: ScreenerRow,
        analyst_detail: CompanyAnalystDetail | None = None,
        financial_detail: CompanyFinancialDetail | None = None,
        chart_data: CompanyChartsData | None = None,
        peer_comparison: PeerComparisonData | None = None,
    ) -> None:
        self._current_row = row
        self._in_watchlist = analyst_detail is not None and analyst_detail.watchlist_status is not None

        if self._in_watchlist:
            self._watchlist_btn.setText("Remove Watchlist")
            self._watchlist_btn.setStyleSheet(
                f"background-color: {C_BG_SEC}; color: {C_TEXT_MAIN}; border: 1px solid {C_BORDER};"
            )
        else:
            self._watchlist_btn.setText("Add to Watchlist")
            self._watchlist_btn.setStyleSheet(f"background-color: {C_ACC_PRI}; color: #FFFFFF; border: none;")

        ccy = financial_detail.currency if financial_detail else "EUR"

        self.lbl_name.setText(row.name)
        self.lbl_ticker.setText(row.ticker or _NA)

        # Enrich sector line with industry and location
        location_parts = []
        if financial_detail:
            if financial_detail.city:
                location_parts.append(financial_detail.city)
            if row.country:
                location_parts.append(row.country)
        location = ", ".join(location_parts) if location_parts else (row.country or "Unknown Location")

        sector_line = row.sector or "Unknown Sector"
        if financial_detail and financial_detail.industry:
            sector_line += f" ({financial_detail.industry})"

        self.lbl_sector.setText(f"{sector_line} | {location} | {ccy}")

        price = financial_detail.current_price if financial_detail else None
        self.lbl_price.setText(f"{_fmt(price)} {ccy}" if price else _NA)

        mcap = financial_detail.market_cap if financial_detail else None
        ev_model = financial_detail.enterprise_value if financial_detail else None
        ev_yahoo = financial_detail.enterprise_value_yahoo if financial_detail else None
        self.lbl_mcap.setText(f"MCap: {_fmt_large(mcap, ccy)}")
        self.lbl_ev_model.setText(f"EV (Model): {_fmt_large(ev_model, ccy)}")
        self.lbl_ev_yahoo.setText(f"EV (Yahoo): {_fmt_large(ev_yahoo, ccy)}")

        target_price = financial_detail.analyst_target_price if financial_detail else None
        upside = financial_detail.analyst_target_upside if financial_detail else None
        downside = financial_detail.analyst_target_downside if financial_detail else None
        recommendation = financial_detail.analyst_recommendation if financial_detail else None
        analyst_count = financial_detail.analyst_count if financial_detail else None
        forward_pe = financial_detail.forward_pe if financial_detail else None
        beta = financial_detail.beta if financial_detail else None
        confidence = financial_detail.confidence_level if financial_detail else None
        last_refresh = financial_detail.last_refresh_at if financial_detail else None
        self.lbl_target.setText(f"Target: {_fmt(target_price)} {ccy}" if target_price is not None else "Target: -")
        if upside is None:
            self.lbl_upside.setText("Upside/Downside: -")
        else:
            upside_txt = _fmt_pct(upside)
            downside_txt = _fmt_pct(downside) if downside is not None else "-"
            self.lbl_upside.setText(f"Upside/Downside: {upside_txt} / {downside_txt}")
        self.lbl_reco.setText(f"Reco: {recommendation}" if recommendation else "Reco: -")
        self.lbl_analyst_count.setText(f"Analysts: {analyst_count}" if analyst_count is not None else "Analysts: -")
        self.lbl_forward_pe.setText(f"Fwd P/E: {_fmt_ratio(forward_pe)}" if forward_pe is not None else "Fwd P/E: -")
        self.lbl_beta.setText(f"Beta: {_fmt(beta)}" if beta is not None else "Beta: -")
        self.lbl_confidence.setText(f"Confidence: {(confidence or '-').upper()}")
        self.lbl_last_refresh.setText(
            f"Last refresh: {last_refresh.strftime('%Y-%m-%d %H:%M')}"
            if last_refresh is not None
            else "Last refresh: -"
        )

        score = row.total_score if analyst_detail is None else analyst_detail.total_score
        score_text = "N/A"
        score_color = C_TEXT_SEC
        if score is not None:
            score_text = f"Score {score:.0f}"
            if score >= 70:
                score_color = C_POS
                story = "Top Tier"
            elif score >= 40:
                score_color = C_WARN
                story = "Mid Tier"
            else:
                score_color = C_NEG
                story = "Bottom Tier"
            score_text += f" ({story})"

        self.badge_score.setText(score_text)
        self.badge_score.setStyleSheet(
            f"color: {score_color}; background-color: {score_color}20; border: 1px solid {score_color};"
        )

        rank = row.sector_rank if analyst_detail is None else analyst_detail.sector_rank
        self.badge_rank.setText(f"Rank #{rank}" if rank else "Rank: -")

        q_score = row.data_quality_score
        q_score_pct = _to_quality_percent(q_score)
        q_color = C_POS if q_score_pct and q_score_pct >= 80 else C_WARN if q_score_pct and q_score_pct >= 50 else C_NEG
        self.badge_quality.setText(f"Data Qty: {_fmt_quality_pct(q_score)}")
        self.badge_quality.setStyleSheet(
            f"color: {q_color}; background-color: {q_color}20; border: 1px solid {q_color};"
        )
        self.lbl_q_score.setText(f"Data Quality Score: {_fmt_quality_pct(q_score)}")

        wl_status = analyst_detail.watchlist_status if analyst_detail else _NOT_IN_WATCHLIST
        wl_color = C_ACC_SEC if wl_status != _NOT_IN_WATCHLIST else C_TEXT_SEC
        self.badge_watchlist.setText(f"WL: {wl_status}")
        self.badge_watchlist.setStyleSheet(
            f"color: {wl_color}; background-color: {wl_color}20; border: 1px solid {wl_color};"
        )

        # KPIs
        self._update_kpi("Rev Growth", financial_detail.revenue_growth if financial_detail else None, _fmt_pct)
        self._update_kpi("Operating Margin", financial_detail.operating_margin if financial_detail else None, _fmt_pct)
        self._update_kpi("Gross Margin", financial_detail.gross_margin if financial_detail else None, _fmt_pct)
        self._update_kpi("ROIC", financial_detail.roic if financial_detail else None, _fmt_pct)
        self._update_kpi("ROE", financial_detail.roe if financial_detail else None, _fmt_pct)
        self._update_kpi("FCF Yield", financial_detail.fcf_yield if financial_detail else None, _fmt_pct)
        self._update_kpi(
            "Net Debt / EBITDA", financial_detail.net_debt_to_ebitda if financial_detail else None, _fmt_ratio
        )
        self._update_kpi("EV / EBITDA", financial_detail.ev_ebitda if financial_detail else None, _fmt_ratio)
        self._update_kpi("P/E", financial_detail.pe_ratio if financial_detail else None, _fmt_ratio)

        self._populate_fin_table(financial_detail)
        self._populate_charts(chart_data)
        self._populate_memo(analyst_detail, financial_detail)
        self._populate_peer_comparison(peer_comparison)
        self._populate_ownership(peer_comparison, financial_detail)
        self._populate_quality(financial_detail, q_score)
        self._populate_profile_card(financial_detail)

    def _populate_peer_comparison(self, peer_comparison: PeerComparisonData | None) -> None:
        if peer_comparison is None:
            self._peer_summary_label.setText("Peer set: -")
            self._peer_analyst_label.setText("Analyst view: -")
            self._peer_metric_table.setRowCount(0)
            self._peer_table.setRowCount(0)
            return

        self._peer_summary_label.setText(
            f"Peer set: sector={peer_comparison.sector or '-'} "
            f"| market={peer_comparison.market or '-'} "
            f"| bucket={peer_comparison.market_cap_bucket or '-'} "
            f"| peers={peer_comparison.peer_count}"
        )
        assessment = peer_comparison.analyst_assessment
        self._peer_analyst_label.setText(
            " | ".join(
                [
                    f"Cheaper than peers: {_fmt_bool(assessment.cheaper_than_peers)}",
                    f"Higher quality: {_fmt_bool(assessment.higher_quality_than_peers)}",
                    f"Growth premium justified: {_fmt_bool(assessment.growth_premium_justified)}",
                    f"Balance sheet weaker: {_fmt_bool(assessment.balance_sheet_weaker)}",
                ]
            )
        )

        self._peer_metric_table.setRowCount(len(peer_comparison.metrics))
        for row_index, metric in enumerate(peer_comparison.metrics):
            self._peer_metric_table.setItem(row_index, 0, QTableWidgetItem(metric.label))
            self._peer_metric_table.setItem(row_index, 1, QTableWidgetItem(_fmt(metric.company_value)))
            self._peer_metric_table.setItem(row_index, 2, QTableWidgetItem(_fmt(metric.sector_median)))
            percentile_text = _NA if metric.percentile_rank is None else f"{metric.percentile_rank:.0f}%"
            self._peer_metric_table.setItem(row_index, 3, QTableWidgetItem(percentile_text))
            self._peer_metric_table.setItem(
                row_index,
                4,
                QTableWidgetItem(_fmt_signed_pct(metric.premium_discount_vs_peers)),
            )

        self._peer_table.setRowCount(len(peer_comparison.peer_rows))
        for row_index, peer in enumerate(peer_comparison.peer_rows):
            self._peer_table.setItem(row_index, 0, QTableWidgetItem(peer.ticker or _NA))
            self._peer_table.setItem(row_index, 1, QTableWidgetItem(peer.name))
            self._peer_table.setItem(row_index, 2, QTableWidgetItem(_fmt_large(peer.market_cap)))
            self._peer_table.setItem(row_index, 3, QTableWidgetItem(_fmt_ratio(peer.ev_ebitda)))
            self._peer_table.setItem(row_index, 4, QTableWidgetItem(_fmt_ratio(peer.pe_ratio)))
            self._peer_table.setItem(row_index, 5, QTableWidgetItem(_fmt_pct(peer.fcf_yield)))
            self._peer_table.setItem(row_index, 6, QTableWidgetItem(_fmt_pct(peer.revenue_growth)))
            self._peer_table.setItem(row_index, 7, QTableWidgetItem(_fmt_pct(peer.ebitda_margin)))
            self._peer_table.setItem(row_index, 8, QTableWidgetItem(_fmt_pct(peer.roic)))
            self._peer_table.setItem(row_index, 9, QTableWidgetItem(_fmt_ratio(peer.net_debt_to_ebitda)))

    def _populate_profile_card(self, detail: CompanyFinancialDetail | None) -> None:
        if not detail:
            self._lbl_profile_industry.setText("-")
            self._lbl_profile_location.setText("-")
            self._lbl_profile_employees.setText("-")
            self._lbl_profile_website.setText("-")
            self._lbl_profile_phone.setText("-")
            return

        self._lbl_profile_industry.setText(detail.industry or "-")

        location = detail.country or "-"
        if detail.city:
            location = f"{detail.city}, {location}"
        self._lbl_profile_location.setText(location)

        employees = f"{detail.full_time_employees:,}" if detail.full_time_employees else "-"
        self._lbl_profile_employees.setText(employees)

        self._lbl_profile_website.setText(detail.website or "-")
        self._lbl_profile_phone.setText(detail.phone or "-")
        self._populate_metrics_card(detail)

    def _populate_metrics_card(self, detail: CompanyFinancialDetail | None) -> None:
        if not detail:
            self._lbl_gross_margin.setText("-")
            self._lbl_op_margin.setText("-")
            self._lbl_profit_margin.setText("-")
            self._lbl_roe.setText("-")
            self._lbl_roa.setText("-")
            self._lbl_current_ratio.setText("-")
            self._lbl_quick_ratio.setText("-")
            self._lbl_payout_ratio.setText("-")
            self._lbl_avg_volume.setText("-")
            self._lbl_shares_outstanding.setText("-")
            self._lbl_div_yield.setText("-")
            self._lbl_target_upside.setText("-")
            self._lbl_target_price.setText("-")
            self._lbl_float_shares.setText("-")
            self._lbl_5y_div_yield.setText("-")
            return

        def _fmt_pct(val: float | None) -> str:
            return f"{val * 100:.2f}%" if val is not None else "-"

        def _fmt_val(val: float | None) -> str:
            return f"{val:.2f}" if val is not None else "-"

        self._lbl_gross_margin.setText(_fmt_pct(detail.latest_gross_margins))
        self._lbl_op_margin.setText(_fmt_pct(detail.latest_operating_margins))
        self._lbl_profit_margin.setText(_fmt_pct(detail.latest_profit_margins))
        self._lbl_roe.setText(_fmt_pct(detail.latest_roe))
        self._lbl_roa.setText(_fmt_pct(detail.latest_roa))

        self._lbl_current_ratio.setText(_fmt_val(detail.latest_current_ratio))
        self._lbl_quick_ratio.setText(_fmt_val(detail.latest_quick_ratio))
        self._lbl_payout_ratio.setText(_fmt_pct(detail.latest_payout_ratio))
        self._lbl_avg_volume.setText(_fmt_large(detail.average_daily_volume, detail.currency))
        self._lbl_shares_outstanding.setText(_fmt_large(detail.shares_outstanding, detail.currency))

        self._lbl_div_yield.setText(_fmt_pct(detail.latest_dividend_yield))
        self._lbl_target_upside.setText(_fmt_pct(detail.analyst_target_upside))
        self._lbl_target_price.setText(
            f"{detail.analyst_target_price:.2f} {detail.currency}" if detail.analyst_target_price is not None else "-"
        )
        self._lbl_float_shares.setText(_fmt_large(detail.float_shares, detail.currency))

        # 5yAvg yield from yf is usually in % (e.g. 2.5), while current yield is 0.025.
        if detail.latest_five_year_avg_dividend_yield is not None:
            self._lbl_5y_div_yield.setText(f"{detail.latest_five_year_avg_dividend_yield:.2f}%")
        else:
            self._lbl_5y_div_yield.setText("-")

    def _populate_memo(
        self,
        analyst_detail: CompanyAnalystDetail | None,
        financial_detail: CompanyFinancialDetail | None,
    ) -> None:
        summary_text = financial_detail.business_summary if financial_detail else None
        self._memo_business_summary.setPlainText(summary_text or "")

        score_explanation = analyst_detail.score_explanation if analyst_detail else None

        # Strengths
        strengths = score_explanation.strengths if score_explanation and score_explanation.strengths else []
        if strengths:
            self.txt_strengths.setText("• " + "\n• ".join(strengths))
        else:
            self.txt_strengths.setText("No major strengths identified.")

        # Weaknesses
        weaknesses = score_explanation.weaknesses if score_explanation and score_explanation.weaknesses else []
        if weaknesses:
            self.txt_weaknesses.setText("• " + "\n• ".join(weaknesses))
        else:
            self.txt_weaknesses.setText("No major weaknesses identified.")

        # Red flags (from memo.key_risks or extremely bad drivers)
        red_flags = []
        if analyst_detail and analyst_detail.analyst_memo and analyst_detail.analyst_memo.key_risks:
            red_flags.append(analyst_detail.analyst_memo.key_risks)

        if red_flags:
            self.txt_red.setText("• " + "\n• ".join(red_flags))
        else:
            self.txt_red.setText("No red flags identified.")

        # Memo text edits
        if analyst_detail:
            self.input_status.setCurrentText(analyst_detail.watchlist_status or WATCHLIST_STATUS_WATCHING)
            self.input_excluded.setChecked(analyst_detail.watchlist_is_excluded)
            self.input_notes.setText(analyst_detail.watchlist_notes or "")

            review_at_str = ""
            if analyst_detail.next_review_at:
                review_at_str = analyst_detail.next_review_at.strftime("%Y-%m-%d")
            self.input_review_at.setText(review_at_str)

            memo = analyst_detail.analyst_memo
            if memo:
                self.input_thesis.setPlainText(memo.investment_thesis or "")
                self.input_risks.setPlainText(memo.key_risks or "")
                self.input_catalysts.setPlainText(memo.catalysts or "")
                self.input_val.setPlainText(memo.valuation_notes or "")
                self.input_action.setPlainText(memo.next_action or "")
            else:
                self.input_thesis.clear()
                self.input_risks.clear()
                self.input_catalysts.clear()
                self.input_val.clear()
                self.input_action.clear()
        else:
            self.input_status.setCurrentText(WATCHLIST_STATUS_WATCHING)
            self.input_excluded.setChecked(False)
            self.input_notes.clear()
            self.input_review_at.clear()
            self.input_thesis.clear()
            self.input_risks.clear()
            self.input_catalysts.clear()
            self.input_val.clear()
            self.input_action.clear()

    def _populate_ownership(
        self,
        peer_comparison: PeerComparisonData | None,
        financial_detail: CompanyFinancialDetail | None,
    ) -> None:
        _ = peer_comparison
        self._lbl_ceo.setText(
            financial_detail.ceo_name if financial_detail and financial_detail.ceo_name else "Not available"
        )
        self._lbl_cfo.setText(
            financial_detail.cfo_name if financial_detail and financial_detail.cfo_name else "Not available"
        )

        refresh_text = "-"
        if financial_detail and financial_detail.last_refresh_at:
            refresh_text = financial_detail.last_refresh_at.strftime("%Y-%m-%d %H:%M")

        major_count = len(financial_detail.major_holders) if financial_detail else 0
        institutional_count = len(financial_detail.institutional_holders) if financial_detail else 0
        insider_count = len(financial_detail.insider_activity) if financial_detail else 0

        if (major_count + institutional_count + insider_count) == 0:
            self._lbl_ownership_status.setText(
                "Ownership data is currently unavailable from provider feeds. "
                f"Last refresh: {refresh_text}. This is common on less-covered tickers."
            )
        else:
            self._lbl_ownership_status.setText(
                f"Ownership feed loaded ({major_count} major metrics, "
                f"{institutional_count} institutions, {insider_count} insider rows). "
                f"Last refresh: {refresh_text}."
            )

        def _set_empty_table(table: QTableWidget, column_count: int, message: str) -> None:
            table.setRowCount(1)
            table.setItem(0, 0, QTableWidgetItem(message))
            for col_index in range(1, column_count):
                table.setItem(0, col_index, QTableWidgetItem("-"))

        top_holders = financial_detail.top_shareholders if financial_detail else ()
        if not top_holders:
            _set_empty_table(
                self._tbl_top_holders,
                4,
                "No top shareholders available (Yahoo coverage is limited for this ticker).",
            )
        else:
            self._tbl_top_holders.setRowCount(len(top_holders))
            for row_index, holder in enumerate(top_holders):
                holder_type = holder.holder_type.replace("_", " ").title()
                self._tbl_top_holders.setItem(row_index, 0, QTableWidgetItem(holder.holder_name))
                self._tbl_top_holders.setItem(row_index, 1, QTableWidgetItem(holder_type))
                self._tbl_top_holders.setItem(row_index, 2, QTableWidgetItem(_fmt_pct(holder.weight)))
                reported = holder.date_reported.isoformat() if holder.date_reported is not None else "-"
                self._tbl_top_holders.setItem(row_index, 3, QTableWidgetItem(reported))

        institutional_holders = financial_detail.institutional_holders if financial_detail else ()
        if not institutional_holders:
            _set_empty_table(
                self._tbl_institutional_holders,
                3,
                "No institutional holdings available for this ticker.",
            )
        else:
            self._tbl_institutional_holders.setRowCount(len(institutional_holders))
            for row_index, holder in enumerate(institutional_holders):
                self._tbl_institutional_holders.setItem(row_index, 0, QTableWidgetItem(holder.holder_name))
                self._tbl_institutional_holders.setItem(row_index, 1, QTableWidgetItem(_fmt_pct(holder.weight)))
                reported = holder.date_reported.isoformat() if holder.date_reported is not None else "-"
                self._tbl_institutional_holders.setItem(row_index, 2, QTableWidgetItem(reported))

        insider_activity = financial_detail.insider_activity if financial_detail else ()
        if not insider_activity:
            _set_empty_table(
                self._tbl_insider_activity,
                4,
                "No recent insider transactions disclosed.",
            )
            return

        self._tbl_insider_activity.setRowCount(len(insider_activity))
        for row_index, insider in enumerate(insider_activity):
            self._tbl_insider_activity.setItem(row_index, 0, QTableWidgetItem(insider.insider_name or "-"))
            self._tbl_insider_activity.setItem(row_index, 1, QTableWidgetItem(insider.relation or "-"))
            activity = insider.transaction_text or insider.ownership or "-"
            self._tbl_insider_activity.setItem(row_index, 2, QTableWidgetItem(activity))
            date_text = insider.start_date.isoformat() if insider.start_date is not None else "-"
            self._tbl_insider_activity.setItem(row_index, 3, QTableWidgetItem(date_text))

    def _populate_quality(self, detail: CompanyFinancialDetail | None, q_score: float | None) -> None:
        self.lbl_q_score.setText(f"Data Quality Score: {_fmt_quality_pct(q_score)}")
        if detail is None:
            self.lbl_q_provider.setText("Provider: -")
            self.lbl_q_snapshot_source.setText("Snapshot source: -")
            self.lbl_q_refresh.setText("Last refresh: -")
            self.lbl_q_snapshot_date.setText("Snapshot date: -")
            self.lbl_q_confidence.setText("Confidence: -")
            self.lbl_q_desc.setText("Missing fields: -")
            return

        self.lbl_q_provider.setText(f"Provider: {detail.provider_source or '-'}")
        self.lbl_q_snapshot_source.setText(f"Snapshot source: {detail.snapshot_source or '-'}")
        self.lbl_q_refresh.setText(
            f"Last refresh: {detail.last_refresh_at.strftime('%Y-%m-%d %H:%M')}"
            if detail.last_refresh_at
            else "Last refresh: -"
        )
        self.lbl_q_snapshot_date.setText(
            f"Snapshot date: {detail.snapshot_date.isoformat()}" if detail.snapshot_date else "Snapshot date: -"
        )
        self.lbl_q_confidence.setText(f"Confidence: {(detail.confidence_level or '-').upper()}")
        missing_fields = ", ".join(detail.missing_fields) if detail.missing_fields else "none"
        self.lbl_q_desc.setText(f"Missing fields: {missing_fields}")

    def _populate_charts(self, chart_data: CompanyChartsData | None) -> None:
        # Clear existing charts
        while self.chart_container.count():
            item = self.chart_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not chart_data:
            return

        def _add_chart(chart: QChart):
            cv = QChartView(chart)
            cv.setRenderHint(QPainter.RenderHint.Antialiasing)
            cv.setMinimumHeight(280)
            cv.setStyleSheet(f"background-color: {C_BG_CARD}; border: 1px solid {C_BORDER}; border-radius: 6px;")
            self.chart_container.addWidget(cv)

        # 1. Price
        chart_price = QChart()
        chart_price.setTitle("Price History (Base 100)")
        chart_price.legend().hide()
        chart_price.setBackgroundBrush(QColor(C_BG_CARD))
        chart_price.setTitleBrush(QColor(C_TEXT_MAIN))

        series_price = QLineSeries()
        pen = QPen(QColor(C_ACC_PRI))
        pen.setWidth(2)
        series_price.setPen(pen)

        if chart_data.price_points:
            base = chart_data.price_points[0].value
            if base == 0:
                base = 1
            vals = []
            for p in chart_data.price_points:
                dt = QDateTime(p.point_date.year, p.point_date.month, p.point_date.day, 0, 0, 0)
                norm = (p.value / base) * 100
                series_price.append(float(dt.toMSecsSinceEpoch()), norm)
                vals.append(norm)

            chart_price.addSeries(series_price)
            ax = QDateTimeAxis()
            ax.setFormat("MMM yyyy")
            ax.setLabelsBrush(QColor(C_TEXT_SEC))
            chart_price.addAxis(ax, Qt.AlignmentFlag.AlignBottom)
            series_price.attachAxis(ax)

            ay = QValueAxis()
            ay.setLabelFormat("%.0f")
            ay.setLabelsBrush(QColor(C_TEXT_SEC))
            ay.setRange(min(vals) * 0.9, max(vals) * 1.1)
            chart_price.addAxis(ay, Qt.AlignmentFlag.AlignLeft)
            series_price.attachAxis(ay)

        _add_chart(chart_price)

        # 2. Revenue & EBITDA
        chart_rev = QChart()
        chart_rev.setTitle("Revenue & EBITDA (M)")
        chart_rev.setBackgroundBrush(QColor(C_BG_CARD))
        chart_rev.setTitleBrush(QColor(C_TEXT_MAIN))
        chart_rev.legend().setLabelBrush(QColor(C_TEXT_SEC))

        s_rev = QLineSeries()
        s_rev.setName("Revenue")
        p_rev = QPen(QColor(C_ACC_PRI))
        p_rev.setWidth(2)
        s_rev.setPen(p_rev)

        s_ebitda = QLineSeries()
        s_ebitda.setName("EBITDA")
        p_ebitda = QPen(QColor(C_POS))
        p_ebitda.setWidth(2)
        s_ebitda.setPen(p_ebitda)

        if chart_data.fundamentals.revenue_points:
            years = []
            vals = []
            for p in chart_data.fundamentals.revenue_points:
                s_rev.append(float(p.fiscal_year), p.value / 1_000_000)
                years.append(p.fiscal_year)
                vals.append(p.value / 1_000_000)

            for p in chart_data.fundamentals.operating_income_points:
                s_ebitda.append(float(p.fiscal_year), p.value / 1_000_000)
                vals.append(p.value / 1_000_000)

            chart_rev.addSeries(s_rev)
            chart_rev.addSeries(s_ebitda)

            ax = QValueAxis()
            ax.setLabelFormat("%.0f")
            ax.setLabelsBrush(QColor(C_TEXT_SEC))
            ax.setRange(min(years) - 0.5, max(years) + 0.5)
            chart_rev.addAxis(ax, Qt.AlignmentFlag.AlignBottom)
            s_rev.attachAxis(ax)
            s_ebitda.attachAxis(ax)

            ay = QValueAxis()
            ay.setLabelFormat("%.0f")
            ay.setLabelsBrush(QColor(C_TEXT_SEC))
            ay.setRange(min(vals) * 0.9 if min(vals) < 0 else 0, max(vals) * 1.1)
            chart_rev.addAxis(ay, Qt.AlignmentFlag.AlignLeft)
            s_rev.attachAxis(ay)
            s_ebitda.attachAxis(ay)

        _add_chart(chart_rev)

        # 3. Margin Evolution
        chart_margin = QChart()
        chart_margin.setTitle("Margin Evolution (%)")
        chart_margin.setBackgroundBrush(QColor(C_BG_CARD))
        chart_margin.setTitleBrush(QColor(C_TEXT_MAIN))
        chart_margin.legend().setLabelBrush(QColor(C_TEXT_SEC))

        s_margin = QLineSeries()
        s_margin.setName("Op. Margin")
        p_margin = QPen(QColor(C_ACC_SEC))
        p_margin.setWidth(2)
        s_margin.setPen(p_margin)

        if chart_data.fundamentals.margin_points:
            years = []
            vals = []
            for p in chart_data.fundamentals.margin_points:
                s_margin.append(float(p.fiscal_year), p.value * 100)
                years.append(p.fiscal_year)
                vals.append(p.value * 100)

            chart_margin.addSeries(s_margin)

            ax = QValueAxis()
            ax.setLabelFormat("%.0f")
            ax.setLabelsBrush(QColor(C_TEXT_SEC))
            ax.setRange(min(years) - 0.5, max(years) + 0.5)
            chart_margin.addAxis(ax, Qt.AlignmentFlag.AlignBottom)
            s_margin.attachAxis(ax)

            ay = QValueAxis()
            ay.setLabelFormat("%.1f")
            ay.setLabelsBrush(QColor(C_TEXT_SEC))
            ay.setRange(min(vals) * 0.9 if min(vals) < 0 else 0, max(vals) * 1.1)
            chart_margin.addAxis(ay, Qt.AlignmentFlag.AlignLeft)
            s_margin.attachAxis(ay)

        _add_chart(chart_margin)

        # 4. Score Breakdown
        chart_score = QChart()
        chart_score.setTitle("Score Breakdown")
        chart_score.legend().hide()
        chart_score.setBackgroundBrush(QColor(C_BG_CARD))
        chart_score.setTitleBrush(QColor(C_TEXT_MAIN))

        if chart_data.score_breakdown:
            bar_set = QBarSet("Score")
            cats = []
            max_score = 0
            for p in chart_data.score_breakdown:
                bar_set.append(p.score)
                cats.append(p.label)
                max_score = max(max_score, p.score)

            bar_set.setColor(QColor(C_ACC_PRI))
            s_score = QBarSeries()
            s_score.append(bar_set)
            chart_score.addSeries(s_score)

            ax = QBarCategoryAxis()
            ax.append(cats)
            ax.setLabelsBrush(QColor(C_TEXT_SEC))
            chart_score.addAxis(ax, Qt.AlignmentFlag.AlignBottom)
            s_score.attachAxis(ax)

            ay = QValueAxis()
            ay.setLabelFormat("%.0f")
            ay.setLabelsBrush(QColor(C_TEXT_SEC))
            ay.setRange(0, max(100.0, max_score * 1.1))
            chart_score.addAxis(ay, Qt.AlignmentFlag.AlignLeft)
            s_score.attachAxis(ay)

        _add_chart(chart_score)

    def _update_kpi(self, key: str, value: float | None, fmt_func) -> None:
        lbl_val, lbl_sig = self.kpi_widgets[key]
        lbl_val.setText(fmt_func(value))
        sig_text, sig_color = _kpi_signal(key, value)
        lbl_sig.setText(sig_text)
        lbl_sig.setStyleSheet(f"color: {sig_color}; font-weight: bold; font-size: 11px; border: none;")

        font_st = "font-size: 18px; font-weight: 600; font-family: 'IBM Plex Sans', 'JetBrains Mono', monospace;"
        if sig_color == C_POS:
            lbl_val.setStyleSheet(f"color: {C_POS}; {font_st}")
        elif sig_color == C_NEG:
            lbl_val.setStyleSheet(f"color: {C_NEG}; {font_st}")
        else:
            lbl_val.setStyleSheet(f"color: {C_TEXT_MAIN}; {font_st}")

    def _populate_fin_table(self, detail: CompanyFinancialDetail | None) -> None:
        self.fin_table.clear()
        self.fin_table.setRowCount(0)
        self.fin_table.setColumnCount(0)

        if not detail or not getattr(detail, "historical_fundamentals", None):
            return

        hf = detail.historical_fundamentals
        periods = [
            ("Revenue", hf.revenue_history, _fmt_large),
            ("EBITDA", getattr(hf, "ebitda_history", []), _fmt_large),
            ("Net Income", hf.net_income_history, _fmt_large),
            ("FCF", hf.free_cash_flow_history, _fmt_large),
            ("Net Debt", hf.net_debt_history, _fmt_large),
        ]

        years_set = set()
        for _, history, _ in periods:
            for point in history:
                years_set.add(point.fiscal_year)

        years = sorted(list(years_set), reverse=True)[:5]
        if not years:
            return

        headers = ["Metric"] + [str(y) for y in years]
        self.fin_table.setColumnCount(len(headers))
        self.fin_table.setHorizontalHeaderLabels(headers)
        self.fin_table.setRowCount(len(periods))

        for row_idx, (label, history, fmt_func) in enumerate(periods):
            item = QTableWidgetItem(label)
            item.setForeground(QColor(C_TEXT_MAIN))
            self.fin_table.setItem(row_idx, 0, item)

            h_dict = {p.fiscal_year: p for p in history}
            for col_idx, year in enumerate(years):
                point = h_dict.get(year)
                val_str = fmt_func(point.value, detail.currency) if point else _NA
                cell = QTableWidgetItem(val_str)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                cell.setForeground(QColor(C_TEXT_SEC if not point else C_TEXT_MAIN))
                self.fin_table.setItem(row_idx, col_idx + 1, cell)

    def _toggle_watchlist(self) -> None:
        if self._current_row is None:
            return
        if self._in_watchlist:
            self.remove_watchlist_requested.emit(self._current_row.company_id)
        else:
            self.add_watchlist_requested.emit(self._current_row.company_id, "")

    def _on_refresh_clicked(self) -> None:
        if self._current_row is None:
            return
        self.refresh_company_requested.emit(self._current_row.company_id)

    def _on_save_clicked(self) -> None:
        if self._current_row is None:
            return

        status = self.input_status.currentData()
        notes = self.input_notes.text().strip()
        is_excluded = self.input_excluded.isChecked()
        thesis = self.input_thesis.toPlainText().strip()
        risks = self.input_risks.toPlainText().strip()
        catalysts = self.input_catalysts.toPlainText().strip()
        val_notes = self.input_val.toPlainText().strip()
        next_action = self.input_action.toPlainText().strip()
        review_at = self.input_review_at.text().strip()

        self.save_watchlist_requested.emit(
            self._current_row.company_id,
            status,
            notes,
            is_excluded,
            thesis,
            risks,
            catalysts,
            val_notes,
            next_action,
            review_at,
        )

    def clear(self) -> None:
        self._current_row = None
        self._in_watchlist = False
        self.lbl_name.setText("-")
        self.lbl_ticker.setText("-")
        self.lbl_sector.setText("-")
        self.lbl_price.setText("-")
        self.lbl_mcap.setText("-")
        self.lbl_ev_model.setText("-")
        self.lbl_ev_yahoo.setText("-")
        self.lbl_target.setText("Target: -")
        self.lbl_upside.setText("Upside/Downside: -")
        self.lbl_reco.setText("Reco: -")
        self.lbl_analyst_count.setText("Analysts: -")
        self.lbl_forward_pe.setText("Fwd P/E: -")
        self.lbl_beta.setText("Beta: -")
        self.lbl_confidence.setText("Confidence: -")
        self.lbl_last_refresh.setText("Last refresh: -")

        font_st = "font-size: 18px; font-weight: 600; font-family: 'IBM Plex Sans', 'JetBrains Mono', monospace;"
        for lbl_val, lbl_sig in self.kpi_widgets.values():
            lbl_val.setText("-")
            lbl_val.setStyleSheet(f"color: {C_TEXT_MAIN}; {font_st}")
            lbl_sig.setText("-")

        self.fin_table.clear()
        self.fin_table.setRowCount(0)
        self.fin_table.setColumnCount(0)

        self.input_status.setCurrentIndex(0)
        self.input_excluded.setChecked(False)
        self.input_notes.clear()
        self.input_review_at.clear()
        self.input_thesis.clear()
        self.input_risks.clear()
        self.input_catalysts.clear()
        self.input_val.clear()
        self.input_action.clear()

        # Reset profile card
        self._lbl_profile_industry.setText("-")
        self._lbl_profile_location.setText("-")
        self._lbl_profile_employees.setText("-")
        self._lbl_profile_website.setText("-")
        self._lbl_profile_phone.setText("-")
        self._memo_business_summary.clear()
        self._populate_metrics_card(None)
        self._populate_peer_comparison(None)
        self._populate_ownership(None, None)
        self._populate_quality(None, None)

        while self.chart_container.count():
            item = self.chart_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
