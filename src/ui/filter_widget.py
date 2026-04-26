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

from src.services.screening_service import UniverseScreeningFilters, UniverseScreeningSortField

_SECTOR_PLACEHOLDER = "ex: energy"
_MIN_SCORE_PLACEHOLDER = "ex: 70.0"
_TOP_N_PLACEHOLDER = "ex: 25"
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

        self._scored_only_input = QCheckBox("Sociétés scorées uniquement")

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
        form.addRow("", self._scored_only_input)
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
        top_n = _parse_int(self._top_n_input.text())
        sort_by = cast(UniverseScreeningSortField, self._sort_by_input.currentData() or "rank")
        descending = bool(self._sort_order_input.currentData())
        self.filters_applied.emit(
            UniverseScreeningFilters(
                sector=sector,
                min_total_score=min_total_score,
                scored_only=self._scored_only_input.isChecked(),
                top_n=top_n,
                sort_by=sort_by,
                descending=descending,
            )
        )

    def _on_reset(self) -> None:
        self._sector_input.clear()
        self._min_score_input.clear()
        self._scored_only_input.setChecked(False)
        self._top_n_input.clear()
        self._sort_by_input.setCurrentIndex(0)
        self._sort_order_input.setCurrentIndex(0)
        self.filters_applied.emit(UniverseScreeningFilters())
