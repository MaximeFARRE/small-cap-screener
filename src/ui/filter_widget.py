from __future__ import annotations

from typing import cast

from PySide6.QtCore import Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models.watchlist_entry import (
    WATCHLIST_STATUS_CONVICTION,
    WATCHLIST_STATUS_REJECTED,
    WATCHLIST_STATUS_REVIEW,
    WATCHLIST_STATUS_WATCHING,
)
from src.services.screening_service import (
    UniverseScreeningFilters,
    UniverseScreeningSortField,
    WatchlistExclusionFilter,
    WatchlistScopeFilter,
)

_SECTOR_PLACEHOLDER = "ex: energy"
_MIN_SCORE_PLACEHOLDER = "ex: 70.0"
_MIN_QUALITY_PLACEHOLDER = "ex: 0.6"
_TOP_N_PLACEHOLDER = "ex: 25"
_WATCHLIST_SCOPE_OPTIONS: list[tuple[str, str]] = [
    ("Toutes sociétés", "all"),
    ("Watchlist uniquement", "watchlist_only"),
    ("Hors watchlist uniquement", "non_watchlist_only"),
]
_WATCHLIST_STATUS_OPTIONS: list[tuple[str, str | None]] = [
    ("Tous statuts", None),
    ("watching", WATCHLIST_STATUS_WATCHING),
    ("review", WATCHLIST_STATUS_REVIEW),
    ("rejected", WATCHLIST_STATUS_REJECTED),
    ("conviction", WATCHLIST_STATUS_CONVICTION),
]
_EXCLUSION_FILTER_OPTIONS: list[tuple[str, str]] = [
    ("Non exclues uniquement", "non_excluded_only"),
    ("Exclues uniquement", "excluded_only"),
    ("Toutes (exclues + non exclues)", "all"),
]
_SORT_OPTIONS: list[tuple[str, UniverseScreeningSortField]] = [
    ("Rang global", "rank"),
    ("Score total", "total_score"),
    ("Quality score", "quality_score"),
    ("Value score", "value_score"),
    ("Growth score", "growth_score"),
    ("Risk score", "risk_score"),
    ("Ticker", "ticker"),
]
_ORDER_OPTIONS: list[tuple[str, bool]] = [
    ("Ascendant", False),
    ("Descendant", True),
]


def _parse_float(text: str) -> float | None:
    text = text.strip()
    if not text:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def _parse_int(text: str) -> int | None:
    text = text.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


class FilterWidget(QWidget):
    filters_applied = Signal(UniverseScreeningFilters)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        box = QGroupBox("Filtres")
        form = QFormLayout(box)

        self._sector_input = QLineEdit()
        self._sector_input.setPlaceholderText(_SECTOR_PLACEHOLDER)

        self._min_score_input = QLineEdit()
        score_validator = QDoubleValidator(0.0, 100.0, 2, self)
        score_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self._min_score_input.setValidator(score_validator)
        self._min_score_input.setPlaceholderText(_MIN_SCORE_PLACEHOLDER)

        self._min_quality_input = QLineEdit()
        quality_validator = QDoubleValidator(0.0, 1.0, 2, self)
        quality_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self._min_quality_input.setValidator(quality_validator)
        self._min_quality_input.setPlaceholderText(_MIN_QUALITY_PLACEHOLDER)

        self._max_pe_input = QLineEdit()
        self._max_pe_input.setValidator(QDoubleValidator(0.0, 999.0, 2, self))
        self._max_pe_input.setPlaceholderText("ex: 20.0")

        self._min_growth_input = QLineEdit()
        self._min_growth_input.setValidator(QDoubleValidator(-100.0, 999.0, 2, self))
        self._min_growth_input.setPlaceholderText("ex: 10.0 (%)")

        self._min_margin_input = QLineEdit()
        self._min_margin_input.setValidator(QDoubleValidator(-100.0, 100.0, 2, self))
        self._min_margin_input.setPlaceholderText("ex: 15.0 (%)")

        self._min_market_cap_input = QLineEdit()
        self._min_market_cap_input.setValidator(QDoubleValidator(0.0, 999999999999.0, 0, self))
        self._min_market_cap_input.setPlaceholderText("Min (M€)")

        self._max_market_cap_input = QLineEdit()
        self._max_market_cap_input.setValidator(QDoubleValidator(0.0, 999999999999.0, 0, self))
        self._max_market_cap_input.setPlaceholderText("Max (M€)")

        self._stale_only_input = QCheckBox("Données obsolètes uniquement (>30j)")
        self._scored_only_input = QCheckBox("Sociétés scorées uniquement")

        self._watchlist_scope_input = QComboBox()
        for label, value in _WATCHLIST_SCOPE_OPTIONS:
            self._watchlist_scope_input.addItem(label, value)

        self._watchlist_status_input = QComboBox()
        for label, value in _WATCHLIST_STATUS_OPTIONS:
            self._watchlist_status_input.addItem(label, value)

        self._exclusion_filter_input = QComboBox()
        for label, value in _EXCLUSION_FILTER_OPTIONS:
            self._exclusion_filter_input.addItem(label, value)

        self._top_n_input = QLineEdit()
        self._top_n_input.setValidator(QIntValidator(1, 999_999, self))
        self._top_n_input.setPlaceholderText(_TOP_N_PLACEHOLDER)

        self._sort_by_input = QComboBox()
        for label, value in _SORT_OPTIONS:
            self._sort_by_input.addItem(label, value)

        self._sort_order_input = QComboBox()
        for label, value in _ORDER_OPTIONS:
            self._sort_order_input.addItem(label, value)

        form.addRow("Secteur", self._sector_input)
        form.addRow("Score min", self._min_score_input)
        form.addRow("Qualité min", self._min_quality_input)
        form.addRow("P/E max", self._max_pe_input)
        form.addRow("Croissance min", self._min_growth_input)
        form.addRow("Marge min", self._min_margin_input)
        mc_layout = QHBoxLayout()
        mc_layout.addWidget(self._min_market_cap_input)
        mc_layout.addWidget(self._max_market_cap_input)
        form.addRow("Market Cap", mc_layout)
        form.addRow("", self._stale_only_input)
        form.addRow("", self._scored_only_input)
        form.addRow("Scope watchlist", self._watchlist_scope_input)
        form.addRow("Status watchlist", self._watchlist_status_input)
        form.addRow("Exclusions", self._exclusion_filter_input)
        form.addRow("Top N", self._top_n_input)
        form.addRow("Tri", self._sort_by_input)
        form.addRow("Ordre", self._sort_order_input)

        outer.addWidget(box)

        btn_layout = QHBoxLayout()
        self._apply_btn = QPushButton("Appliquer")
        self._reset_btn = QPushButton("Réinitialiser")
        btn_layout.addWidget(self._apply_btn)
        btn_layout.addWidget(self._reset_btn)
        outer.addLayout(btn_layout)
        outer.addStretch()

        self._apply_btn.clicked.connect(self._on_apply)
        self._reset_btn.clicked.connect(self._on_reset)

    def _on_apply(self) -> None:
        sector = self._sector_input.text().strip() or None
        min_total_score = _parse_float(self._min_score_input.text())
        min_data_quality_score = _parse_float(self._min_quality_input.text())
        max_pe = _parse_float(self._max_pe_input.text())
        min_growth = _parse_float(self._min_growth_input.text())
        min_margin = _parse_float(self._min_margin_input.text())
        min_market_cap = _parse_float(self._min_market_cap_input.text())
        max_market_cap = _parse_float(self._max_market_cap_input.text())

        if min_market_cap is not None:
            min_market_cap *= 1_000_000.0  # Convert to actual currency from M
        if max_market_cap is not None:
            max_market_cap *= 1_000_000.0  # Convert to actual currency from M

        top_n = _parse_int(self._top_n_input.text())
        watchlist_scope = cast(WatchlistScopeFilter, self._watchlist_scope_input.currentData() or "all")
        watchlist_status = self._watchlist_status_input.currentData()
        exclusion_filter = cast(
            WatchlistExclusionFilter, self._exclusion_filter_input.currentData() or "non_excluded_only"
        )
        sort_by = cast(UniverseScreeningSortField, self._sort_by_input.currentData() or "rank")
        descending = bool(self._sort_order_input.currentData())
        include_excluded = exclusion_filter in ("all", "excluded_only")
        self.filters_applied.emit(
            UniverseScreeningFilters(
                sector=sector,
                min_total_score=min_total_score,
                min_data_quality_score=min_data_quality_score,
                max_pe=max_pe,
                min_growth=min_growth,
                min_margin=min_margin,
                min_market_cap=min_market_cap,
                max_market_cap=max_market_cap,
                stale_only=self._stale_only_input.isChecked(),
                scored_only=self._scored_only_input.isChecked(),
                watchlist_scope=watchlist_scope,
                watchlist_status=cast(str | None, watchlist_status),
                exclusion_filter=exclusion_filter,
                include_excluded=include_excluded,
                top_n=top_n,
                sort_by=sort_by,
                descending=descending,
            )
        )

    def _on_reset(self) -> None:
        self._sector_input.clear()
        self._min_score_input.clear()
        self._min_quality_input.clear()
        self._max_pe_input.clear()
        self._min_growth_input.clear()
        self._min_margin_input.clear()
        self._min_market_cap_input.clear()
        self._max_market_cap_input.clear()
        self._stale_only_input.setChecked(False)
        self._scored_only_input.setChecked(False)
        self._watchlist_scope_input.setCurrentIndex(0)
        self._watchlist_status_input.setCurrentIndex(0)
        self._exclusion_filter_input.setCurrentIndex(0)
        self._top_n_input.clear()
        self._sort_by_input.setCurrentIndex(0)
        self._sort_order_input.setCurrentIndex(0)
        self.filters_applied.emit(UniverseScreeningFilters())
