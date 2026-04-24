from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from src.services.ratio_service import CompanyRatios
from src.services.screening_service import ScreeningResult

_HEADERS: list[str] = [
    "Nom",
    "Ticker",
    "Secteur",
    "Marché",
    "Score",
    "P/E",
    "P/B",
    "EV/EBITDA",
    "ROE %",
    "Marge nette %",
    "Dette/CP",
]

_NA = "—"


@dataclass
class ScreenerRow:
    name: str
    ticker: str | None
    sector: str | None
    market: str | None
    result: ScreeningResult

    @property
    def ratios(self) -> CompanyRatios:
        return self.result.ratios

    @property
    def score(self) -> float:
        return self.result.score


def _fmt_ratio(value: float | None, pct: bool = False) -> str:
    if value is None:
        return _NA
    if pct:
        return f"{value * 100:.1f} %"
    return f"{value:.2f}"


class CompanyTableModel(QAbstractTableModel):
    def __init__(self, rows: list[ScreenerRow] | None = None) -> None:
        super().__init__()
        self._rows: list[ScreenerRow] = rows or []

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

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col >= 4:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        match col:
            case 0:
                return row.name
            case 1:
                return row.ticker or _NA
            case 2:
                return row.sector or _NA
            case 3:
                return row.market or _NA
            case 4:
                return f"{row.score:.1f}"
            case 5:
                return _fmt_ratio(row.ratios.pe_ratio)
            case 6:
                return _fmt_ratio(row.ratios.pb_ratio)
            case 7:
                return _fmt_ratio(row.ratios.ev_ebitda)
            case 8:
                return _fmt_ratio(row.ratios.roe, pct=True)
            case 9:
                return _fmt_ratio(row.ratios.net_margin, pct=True)
            case 10:
                return _fmt_ratio(row.ratios.debt_to_equity)
        return None
