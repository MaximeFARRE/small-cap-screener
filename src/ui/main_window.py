from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QFileDialog, QMainWindow, QMessageBox, QSplitter

from src.services import export_service
from src.services.export_service import ExportRow
from src.ui.company_detail_widget import CompanyDetailWidget
from src.ui.company_table_model import ScreenerRow
from src.ui.filter_widget import FilterWidget
from src.ui.screener_widget import ScreenerWidget

WINDOW_TITLE = "Small Cap Screener"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
_SPLITTER_RATIO = (2, 1)
_FILTER_DOCK_WIDTH = 220


def _to_export_row(row: ScreenerRow) -> ExportRow:
    r = row.ratios
    return ExportRow(
        nom=row.name,
        ticker=row.ticker,
        secteur=row.sector,
        marche=row.market,
        score=row.score,
        pe=r.pe_ratio,
        pb=r.pb_ratio,
        ev_ebitda=r.ev_ebitda,
        ev_ebit=r.ev_ebit,
        p_fcf=r.price_to_fcf,
        roe=r.roe,
        roa=r.roa,
        marge_ebit=r.ebit_margin,
        marge_ebitda=r.ebitda_margin,
        marge_nette=r.net_margin,
        dette_cp=r.debt_to_equity,
        dn_ebitda=r.net_debt_to_ebitda,
        mkt_cap=r.mkt_cap,
        ev=r.ev,
        prix=r.price,
        annee_fiscale=r.fiscal_year,
    )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self._setup_ui()

    def _setup_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._screener = ScreenerWidget()
        self._detail = CompanyDetailWidget()

        splitter.addWidget(self._screener)
        splitter.addWidget(self._detail)
        splitter.setStretchFactor(0, _SPLITTER_RATIO[0])
        splitter.setStretchFactor(1, _SPLITTER_RATIO[1])

        self._screener.row_selected.connect(self._detail.load)
        self._screener.selection_cleared.connect(self._detail.clear)

        self.setCentralWidget(splitter)
        self._setup_filter_dock()
        self._setup_menu()

    def _setup_filter_dock(self) -> None:
        self._filters = FilterWidget()
        dock = QDockWidget("Filtres", self)
        dock.setWidget(self._filters)
        features = QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetClosable
        dock.setFeatures(features)
        dock.setMinimumWidth(_FILTER_DOCK_WIDTH)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self._filter_dock = dock

    def _setup_menu(self) -> None:
        file_menu = self.menuBar().addMenu("Fichier")
        file_menu.addAction("Exporter CSV…", self._export_csv)
        file_menu.addAction("Exporter Excel…", self._export_excel)

    def _current_export_rows(self) -> list[ExportRow]:
        return [_to_export_row(r) for r in self._screener.rows()]

    def _export_csv(self) -> None:
        rows = self._current_export_rows()
        if not rows:
            QMessageBox.information(self, "Export", "Aucune donnée à exporter.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter CSV", "screening.csv", "CSV (*.csv)")
        if path:
            export_service.to_csv(rows, Path(path))

    def _export_excel(self) -> None:
        rows = self._current_export_rows()
        if not rows:
            QMessageBox.information(self, "Export", "Aucune donnée à exporter.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter Excel", "screening.xlsx", "Excel (*.xlsx)")
        if path:
            export_service.to_excel(rows, Path(path))
