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
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
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


def _fmt_ratio(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return _NA
    return f"{value:.{decimals}f}x"


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
    if key == "EBITDA Margin":
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
        self._tab_charts = self._create_scroll_tab("Charts")
        self._tab_ownership = self._create_scroll_tab("Ownership")
        self._tab_memo = self._create_scroll_tab("Memo / Thesis")
        self._tab_quality = self._create_scroll_tab("Data Quality")

        self._build_kpis(self._tab_snapshot)
        self._build_financials(self._tab_financials)
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
        self.lbl_ev = QLabel("EV: -")
        self.lbl_ev.setObjectName("HeroSec")
        val_layout.addWidget(self.lbl_mcap)
        val_layout.addWidget(self.lbl_ev)
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

        hero_layout.addLayout(right_layout, stretch=1)

    def _build_kpis(self, parent_layout: QVBoxLayout) -> None:
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(16)

        self.kpi_widgets = {}
        kpi_keys = [
            "Rev Growth",
            "EBITDA Margin",
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
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel("No ownership data available")
        lbl.setStyleSheet(f"color: {C_TEXT_SEC}; font-size: 16px; font-weight: 500;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        parent_layout.addWidget(frame)

    def _build_memo(self, parent_layout: QVBoxLayout) -> None:
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

        self.input_thesis = QTextEdit()
        self.input_thesis.setPlaceholderText("Investment Thesis...")
        self.input_thesis.setMaximumHeight(80)
        memo_layout.addWidget(QLabel("Investment Thesis"))
        memo_layout.addWidget(self.input_thesis)

        self.input_val = QTextEdit()
        self.input_val.setPlaceholderText("Valuation Notes...")
        self.input_val.setMaximumHeight(80)
        memo_layout.addWidget(QLabel("Valuation Notes"))
        memo_layout.addWidget(self.input_val)

        btn_save_memo = QPushButton("Save Memo")
        btn_save_memo.setObjectName("PrimaryBtn")
        btn_save_memo.setCursor(Qt.CursorShape.PointingHandCursor)
        # Note: hook this up in the future
        memo_layout.addWidget(btn_save_memo, alignment=Qt.AlignmentFlag.AlignRight)

        parent_layout.addWidget(memo_frame)

    def _build_quality(self, parent_layout: QVBoxLayout) -> None:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(40, 40, 40, 40)

        self.lbl_q_score = QLabel("Data Quality: -")
        self.lbl_q_score.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.lbl_q_score)

        self.lbl_q_desc = QLabel("Detailed data quality analysis will be available here.")
        self.lbl_q_desc.setStyleSheet(f"color: {C_TEXT_SEC};")
        layout.addWidget(self.lbl_q_desc)

        layout.addStretch()
        parent_layout.addWidget(frame)

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
        self.lbl_sector.setText(f"{row.sector or 'Unknown Sector'} | {ccy}")

        price = financial_detail.current_price if financial_detail else None
        self.lbl_price.setText(f"{_fmt(price)} {ccy}" if price else _NA)

        mcap = financial_detail.market_cap if financial_detail else None
        ev = financial_detail.enterprise_value if financial_detail else None
        self.lbl_mcap.setText(f"MCap: {_fmt_large(mcap, ccy)}")
        self.lbl_ev.setText(f"EV: {_fmt_large(ev, ccy)}")

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
        q_color = C_POS if q_score and q_score >= 0.8 else C_WARN if q_score and q_score >= 0.5 else C_NEG
        self.badge_quality.setText(f"Data Qty: {_fmt_pct(q_score)}")
        self.badge_quality.setStyleSheet(
            f"color: {q_color}; background-color: {q_color}20; border: 1px solid {q_color};"
        )
        self.lbl_q_score.setText(f"Data Quality Score: {_fmt_pct(q_score)}")

        wl_status = analyst_detail.watchlist_status if analyst_detail else _NOT_IN_WATCHLIST
        wl_color = C_ACC_SEC if wl_status != _NOT_IN_WATCHLIST else C_TEXT_SEC
        self.badge_watchlist.setText(f"WL: {wl_status}")
        self.badge_watchlist.setStyleSheet(
            f"color: {wl_color}; background-color: {wl_color}20; border: 1px solid {wl_color};"
        )

        # KPIs
        self._update_kpi("Rev Growth", financial_detail.revenue_growth if financial_detail else None, _fmt_pct)
        self._update_kpi("EBITDA Margin", financial_detail.operating_margin if financial_detail else None, _fmt_pct)
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
        self._populate_memo(analyst_detail)

    def _populate_memo(self, analyst_detail: CompanyAnalystDetail | None) -> None:
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
        if analyst_detail and analyst_detail.analyst_memo:
            self.input_thesis.setPlainText(analyst_detail.analyst_memo.investment_thesis or "")
            self.input_val.setPlainText(analyst_detail.analyst_memo.valuation_notes or "")
        else:
            self.input_thesis.clear()
            self.input_val.clear()

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

    def clear(self) -> None:
        self._current_row = None
        self._in_watchlist = False
        self.lbl_name.setText("-")
        self.lbl_ticker.setText("-")
        self.lbl_sector.setText("-")
        self.lbl_price.setText("-")
        self.lbl_mcap.setText("-")
        self.lbl_ev.setText("-")

        font_st = "font-size: 18px; font-weight: 600; font-family: 'IBM Plex Sans', 'JetBrains Mono', monospace;"
        for lbl_val, lbl_sig in self.kpi_widgets.values():
            lbl_val.setText("-")
            lbl_val.setStyleSheet(f"color: {C_TEXT_MAIN}; {font_st}")
            lbl_sig.setText("-")

        self.fin_table.clear()
        self.fin_table.setRowCount(0)
        self.fin_table.setColumnCount(0)

        while self.chart_container.count():
            item = self.chart_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
