from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from src.services.screening_service import UniverseScreeningEntry

_HEADERS: list[str] = [
    "Ticker",
    "Nom",
    "Secteur",
    "Score total",
    "Rang global",
    "Rang secteur",
    "Qualité data",
]

_NA = "—"


ScreenerRow = UniverseScreeningEntry


def _fmt_score(value: float | None) -> str:
    if value is None:
        return _NA
    return f"{value:.2f}"


def _fmt_quality(value: float | None) -> str:
    if value is None:
        return _NA
    if value >= 0.8:
        return f"{value * 100:.0f}% (Élevée)"
    if value >= 0.5:
        return f"{value * 100:.0f}% (Moyenne)"
    return f"{value * 100:.0f}% (Faible)"


class CompanyTableModel(QAbstractTableModel):
    def __init__(self, rows: list[ScreenerRow] | None = None) -> None:
        super().__init__()
        self._rows: list[ScreenerRow] = rows or []

    def rows(self) -> list[ScreenerRow]:
        return self._rows

    def load(self, rows: list[ScreenerRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return len(_HEADERS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return _HEADERS[section]
        return str(section + 1)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None

        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.ForegroundRole:
            if col == 6 and row.data_quality_score is not None:
                from PySide6.QtGui import QColor

                if row.data_quality_score < 0.5:
                    return QColor("#d62728")  # Red for poor quality
                if row.data_quality_score < 0.8:
                    return QColor("#ff7f0e")  # Orange for medium quality
            return None

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col >= 3:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        match col:
            case 0:
                return row.ticker or _NA
            case 1:
                return row.name
            case 2:
                return row.sector or _NA
            case 3:
                return _fmt_score(row.total_score)
            case 4:
                return str(row.rank) if row.rank is not None else _NA
            case 5:
                return str(row.sector_rank) if row.sector_rank is not None else _NA
            case 6:
                return _fmt_quality(row.data_quality_score)
        return None
