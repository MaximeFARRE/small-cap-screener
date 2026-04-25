from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.services.screening_service import ScreeningCriteria

_EMPTY_PLACEHOLDER = "aucun filtre"

_FIELDS: list[tuple[str, str, bool]] = [
    # (label, attr_name, is_max)
    ("P/E max", "max_pe", True),
    ("P/B max", "max_pb", True),
    ("EV/EBITDA max", "max_ev_ebitda", True),
    ("ROE min (%)", "min_roe", False),
    ("Marge nette min (%)", "min_net_margin", False),
    ("Marge EBIT min (%)", "min_ebit_margin", False),
    ("Dette/CP max", "max_debt_to_equity", True),
    ("DN/EBITDA max", "max_net_debt_to_ebitda", True),
]

_PCT_FIELDS = {"min_roe", "min_net_margin", "min_ebit_margin"}


def _parse(text: str, pct: bool) -> float | None:
    text = text.strip()
    if not text:
        return None
    try:
        value = float(text.replace(",", "."))
        return value / 100.0 if pct else value
    except ValueError:
        return None


class FilterWidget(QWidget):
    filters_applied = Signal(ScreeningCriteria)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._inputs: dict[str, QLineEdit] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        box = QGroupBox("Filtres")
        form = QFormLayout(box)
        validator = QDoubleValidator()
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)

        for label, attr, _ in _FIELDS:
            field = QLineEdit()
            field.setPlaceholderText(_EMPTY_PLACEHOLDER)
            field.setValidator(validator)
            self._inputs[attr] = field
            form.addRow(label, field)

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
        kwargs: dict[str, float | None] = {}
        for _, attr, _ in _FIELDS:
            pct = attr in _PCT_FIELDS
            kwargs[attr] = _parse(self._inputs[attr].text(), pct)
        self.filters_applied.emit(ScreeningCriteria(**kwargs))

    def _on_reset(self) -> None:
        for field in self._inputs.values():
            field.clear()
        self.filters_applied.emit(ScreeningCriteria())
