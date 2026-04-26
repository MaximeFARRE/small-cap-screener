from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDockWidget, QFileDialog, QInputDialog, QMainWindow, QMessageBox, QSplitter

from src.repositories.providers.yfinance_provider import YFinanceProvider
from src.services.company_detail_service import CompanyDetailService
from src.services.financial_data_service import FinancialDataService
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.screening_service import ScreeningService, ScreeningSnapshotSummary, UniverseScreeningFilters
from src.services.ticker_ingestion_service import TickerIngestionService
from src.services.universe_discovery_service import UniverseDiscoveryService
from src.services.watchlist_service import AnalystMemo, WatchlistService
from src.ui.add_ticker_dialog import AddTickerDialog
from src.ui.company_detail_widget import CompanyDetailWidget
from src.ui.company_table_model import ScreenerRow
from src.ui.filter_widget import FilterWidget
from src.ui.screener_widget import ScreenerWidget
from src.ui.screening_snapshot_dialog import ScreeningSnapshotDialog

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
        self._company_detail_service = CompanyDetailService()
        _financial_data_service = FinancialDataService(provider=YFinanceProvider())
        _kpi_snapshot_service = KpiSnapshotService()
        self._ticker_ingestion_service = TickerIngestionService(
            financial_data_service=_financial_data_service,
            kpi_snapshot_service=_kpi_snapshot_service,
        )
        self._universe_discovery_service = UniverseDiscoveryService(
            financial_data_service=_financial_data_service,
            kpi_snapshot_service=_kpi_snapshot_service,
        )
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
        self._detail.refresh_company_requested.connect(self._on_refresh_company_requested)

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
        file_menu.addAction("Ajouter un ticker…", self._open_add_ticker_dialog)
        file_menu.addSeparator()
        self._refresh_universe_action = QAction("Actualiser l'univers", self)
        self._refresh_universe_action.triggered.connect(self._refresh_universe)
        file_menu.addAction(self._refresh_universe_action)
        self._refresh_watchlist_action = QAction("Actualiser la watchlist", self)
        self._refresh_watchlist_action.triggered.connect(self._refresh_watchlist)
        file_menu.addAction(self._refresh_watchlist_action)
        file_menu.addSeparator()
        file_menu.addAction("Sauvegarder ce screening…", self._save_screening_snapshot)
        file_menu.addAction("Snapshots récents…", self._open_recent_screening_snapshots)
        file_menu.addSeparator()
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
        financial_detail = self._company_detail_service.get_financial_detail(row.company_id)
        self._detail.load(row, analyst_detail, financial_detail)

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

    def _on_save_watchlist_requested(
        self,
        company_id: int,
        status: str,
        notes: str,
        is_excluded: bool,
        investment_thesis: str,
        key_risks: str,
        catalysts: str,
        valuation_notes: str,
        next_action: str,
        next_review_at_text: str,
    ) -> None:
        notes_value = notes or None
        memo = AnalystMemo(
            investment_thesis=investment_thesis or None,
            key_risks=key_risks or None,
            catalysts=catalysts or None,
            valuation_notes=valuation_notes or None,
            next_action=next_action or None,
        )
        try:
            next_review_at = _parse_next_review_at(next_review_at_text)
            notes_entry = self._watchlist_service.update_company_notes(company_id, notes_value)
            status_entry = self._watchlist_service.update_company_status(company_id, status)
            excluded_entry = self._watchlist_service.update_company_exclusion(company_id, is_excluded)
            next_review_entry = self._watchlist_service.update_company_next_review(company_id, next_review_at)
            memo_entry = self._watchlist_service.update_company_memo(company_id, memo)
        except ValueError as exc:
            QMessageBox.warning(self, "Watchlist", str(exc))
            return
        if (
            notes_entry is None
            or status_entry is None
            or excluded_entry is None
            or next_review_entry is None
            or memo_entry is None
        ):
            QMessageBox.warning(self, "Watchlist", "Impossible de mettre à jour la société.")
            return
        self._load_scored_universe(selected_company_id=company_id)
        self.statusBar().showMessage("Données analyste mises à jour.", 5000)

    def _open_add_ticker_dialog(self) -> None:
        dialog = AddTickerDialog(self._ticker_ingestion_service, parent=self)
        dialog.ticker_ingested.connect(self._on_ticker_ingested)
        dialog.exec()

    def _on_ticker_ingested(self, company_id: int) -> None:
        self._load_scored_universe(selected_company_id=company_id)
        self.statusBar().showMessage("Ticker importé et screener mis à jour.", 5000)

    def _on_refresh_company_requested(self, company_id: int) -> None:
        self._set_refresh_actions_enabled(False)
        self.statusBar().showMessage("Actualisation en cours…")
        self.repaint()
        result = self._universe_discovery_service.refresh_company(company_id)
        self._set_refresh_actions_enabled(True)
        if not result.success:
            QMessageBox.warning(
                self,
                "Actualisation échouée",
                f"Impossible d'actualiser {result.ticker} : {result.error or 'erreur inconnue'}",
            )
            self.statusBar().clearMessage()
            return
        self._load_scored_universe(selected_company_id=company_id)
        msg = f"{result.ticker} actualisé."
        if result.warnings:
            msg += f" Avertissements : {'; '.join(result.warnings)}"
        self.statusBar().showMessage(msg, 6000)

    def _refresh_universe(self) -> None:
        self._set_refresh_actions_enabled(False)
        self.statusBar().showMessage("Actualisation de l'univers en cours…")
        self.repaint()
        result = self._universe_discovery_service.batch_refresh_universe()
        self._set_refresh_actions_enabled(True)
        self._load_scored_universe(selected_company_id=self._selected_company_id)
        msg = f"Univers actualisé — {result.succeeded}/{result.total} société(s) rafraîchie(s)"
        if result.failed:
            failed_tickers = [r.ticker for r in result.results if not r.success][:3]
            msg += f", {result.failed} échec(s) : {', '.join(t for t in failed_tickers if t)}"
        self.statusBar().showMessage(msg + ".", 8000)

    def _refresh_watchlist(self) -> None:
        self._set_refresh_actions_enabled(False)
        self.statusBar().showMessage("Actualisation de la watchlist en cours…")
        self.repaint()
        result = self._universe_discovery_service.refresh_watchlist()
        self._set_refresh_actions_enabled(True)
        self._load_scored_universe(selected_company_id=self._selected_company_id)
        msg = f"Watchlist actualisée — {result.succeeded}/{result.total} société(s) rafraîchie(s)"
        if result.failed:
            failed_tickers = [r.ticker for r in result.results if not r.success][:3]
            msg += f", {result.failed} échec(s) : {', '.join(t for t in failed_tickers if t)}"
        self.statusBar().showMessage(msg + ".", 8000)

    def _set_refresh_actions_enabled(self, enabled: bool) -> None:
        self._refresh_universe_action.setEnabled(enabled)
        self._refresh_watchlist_action.setEnabled(enabled)

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

    def _save_screening_snapshot(self) -> None:
        default_name = _default_screening_snapshot_name()
        name, accepted = QInputDialog.getText(self, "Sauvegarder screening", "Nom du snapshot", text=default_name)
        if not accepted:
            return
        snapshot_name = name.strip() or default_name
        saved = self._screening_service.save_screening_snapshot(
            self._current_filters,
            name=snapshot_name,
        )
        self.statusBar().showMessage(
            f"Snapshot #{saved.snapshot_id} enregistré ({saved.company_count} société(s)).",
            5000,
        )

    def _open_recent_screening_snapshots(self) -> None:
        summaries = self._screening_service.list_recent_screening_snapshots(limit=20)
        if not summaries:
            QMessageBox.information(self, "Snapshots", "Aucun snapshot enregistré.")
            return
        options = [_snapshot_summary_option(summary) for summary in summaries]
        selected, accepted = QInputDialog.getItem(
            self,
            "Snapshots récents",
            "Choisir un snapshot",
            options,
            0,
            False,
        )
        if not accepted or not selected:
            return
        selected_index = options.index(selected)
        summary = summaries[selected_index]
        snapshot_view = self._screening_service.get_screening_snapshot_view(summary.snapshot_id)
        if snapshot_view is None:
            QMessageBox.warning(self, "Snapshots", "Impossible de charger ce snapshot.")
            return
        comparison_rows = self._screening_service.compare_snapshot_to_current(
            summary.snapshot_id,
            self._current_filters,
        )
        dialog = ScreeningSnapshotDialog(snapshot_view, comparison_rows, parent=self)
        dialog.exec()


def _parse_next_review_at(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(text, "%Y-%m-%d %H:%M")
        except ValueError as exc:
            raise ValueError("invalid next review format, expected YYYY-MM-DD or YYYY-MM-DD HH:MM") from exc


def _default_screening_snapshot_name() -> str:
    return f"screening snapshot {datetime.now():%Y-%m-%d %H:%M}"


def _snapshot_summary_option(summary: ScreeningSnapshotSummary) -> str:
    return (
        f"#{summary.snapshot_id} | {summary.created_at:%Y-%m-%d %H:%M} | "
        f"{summary.company_count} société(s) | {summary.name} | {summary.filters_summary}"
    )
