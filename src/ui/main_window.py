from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QFileDialog, QMainWindow, QMessageBox, QSplitter

from src.services.screening_service import ScreeningService, UniverseScreeningFilters
from src.services.watchlist_service import WatchlistService
from src.ui.company_detail_widget import CompanyDetailWidget
from src.ui.company_table_model import ScreenerRow
from src.ui.filter_widget import FilterWidget
from src.ui.screener_widget import ScreenerWidget

WINDOW_TITLE = "Small Cap Screener"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
_SPLITTER_RATIO = (2, 1)
_FILTER_DOCK_WIDTH = 220


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._screening_service = ScreeningService()
        self._watchlist_service = WatchlistService()
        self._current_filters = UniverseScreeningFilters()
        self._selected_company_id: int | None = None
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self._setup_ui()
        self._load_scored_universe()

    def _setup_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._screener = ScreenerWidget()
        self._detail = CompanyDetailWidget()

        splitter.addWidget(self._screener)
        splitter.addWidget(self._detail)
        splitter.setStretchFactor(0, _SPLITTER_RATIO[0])
        splitter.setStretchFactor(1, _SPLITTER_RATIO[1])

        self._screener.row_selected.connect(self._on_row_selected)
        self._screener.selection_cleared.connect(self._on_selection_cleared)
        self._detail.add_watchlist_requested.connect(self._on_add_watchlist_requested)
        self._detail.remove_watchlist_requested.connect(self._on_remove_watchlist_requested)
        self._detail.save_watchlist_requested.connect(self._on_save_watchlist_requested)

        self.setCentralWidget(splitter)
        self._setup_filter_dock()
        self._setup_menu()

    def _setup_filter_dock(self) -> None:
        self._filters = FilterWidget()
        self._filters.filters_applied.connect(self._on_filters_applied)
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

    def _load_scored_universe(self, selected_company_id: int | None = None) -> None:
        rows = self._screening_service.filter_universe_with_scores(self._current_filters)
        self._screener.load(rows)
        if not rows:
            self._selected_company_id = None
            self._detail.clear()
            self.statusBar().showMessage("Aucune société ne correspond aux filtres.")
            return
        if selected_company_id is not None and self._screener.select_company(selected_company_id):
            self.statusBar().clearMessage()
            return
        self._selected_company_id = None
        self._detail.clear()
        self.statusBar().clearMessage()

    def _on_filters_applied(self, filters: UniverseScreeningFilters) -> None:
        self._current_filters = filters
        self._load_scored_universe(selected_company_id=self._selected_company_id)

    def _on_row_selected(self, row: ScreenerRow) -> None:
        self._selected_company_id = row.company_id
        analyst_detail = self._watchlist_service.get_company_analyst_detail(row.company_id)
        self._detail.load(row, analyst_detail)

    def _on_selection_cleared(self) -> None:
        self._selected_company_id = None
        self._detail.clear()

    def _on_add_watchlist_requested(self, company_id: int, notes: str) -> None:
        notes_value = notes or None
        entry = self._watchlist_service.add_company(company_id, notes=notes_value)
        if entry is None:
            QMessageBox.warning(self, "Watchlist", "Impossible d'ajouter la société à la watchlist.")
            return
        self._load_scored_universe(selected_company_id=company_id)
        self.statusBar().showMessage("Société ajoutée à la watchlist.", 5000)

    def _on_remove_watchlist_requested(self, company_id: int) -> None:
        removed = self._watchlist_service.remove_company(company_id)
        if not removed:
            QMessageBox.information(self, "Watchlist", "La société n'était pas en watchlist.")
        self._load_scored_universe(selected_company_id=company_id)
        self.statusBar().showMessage("Société retirée de la watchlist.", 5000)

    def _on_save_watchlist_requested(self, company_id: int, status: str, notes: str, is_excluded: bool) -> None:
        notes_value = notes or None
        try:
            notes_entry = self._watchlist_service.update_company_notes(company_id, notes_value)
            status_entry = self._watchlist_service.update_company_status(company_id, status)
            excluded_entry = self._watchlist_service.update_company_exclusion(company_id, is_excluded)
        except ValueError as exc:
            QMessageBox.warning(self, "Watchlist", str(exc))
            return
        if notes_entry is None or status_entry is None or excluded_entry is None:
            QMessageBox.warning(self, "Watchlist", "Impossible de mettre à jour la société.")
            return
        self._load_scored_universe(selected_company_id=company_id)
        self.statusBar().showMessage("Données analyste mises à jour.", 5000)

    def _export_csv(self) -> None:
        rows = self._screener.rows()
        if not rows:
            QMessageBox.information(self, "Export", "Aucune donnée à exporter.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter CSV", "screening.csv", "CSV (*.csv)")
        if path:
            csv_content = self._screening_service.export_universe_with_scores_csv(
                self._current_filters,
            )
            Path(path).write_text(csv_content, encoding="utf-8-sig")
