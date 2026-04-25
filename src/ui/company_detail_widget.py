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


def _fmt(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return _NA
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
        for title in ("Société", "Scoring"):
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

        self._set_field("Société", "Nom", row.name)
        self._set_field("Société", "Ticker", row.ticker or _NA)
        self._set_field("Société", "Secteur", row.sector or _NA)
        self._set_field("Scoring", "Score total", _fmt(row.total_score))
        self._set_field("Scoring", "Rang global", str(row.rank) if row.rank is not None else _NA)
        self._set_field("Scoring", "Rang secteur", str(row.sector_rank) if row.sector_rank is not None else _NA)

        self._placeholder.setVisible(False)
        self._scroll.setVisible(True)

    def clear(self) -> None:
        self._scroll.setVisible(False)
        self._placeholder.setVisible(True)
