from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDockWidget, QFileDialog, QInputDialog, QMainWindow, QMessageBox, QStackedWidget

from src.repositories.providers.yfinance_provider import YFinanceProvider
from src.services.backtesting_service import BacktestingService
from src.services.company_charts_service import CompanyChartsService, ScoreBreakdownInput
from src.services.company_detail_service import CompanyDetailService
from src.services.financial_data_service import FinancialDataService
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.maintenance_service import MaintenanceService
from src.services.peer_comparison_service import PeerComparisonService
from src.services.scoring_service import ScoringService
from src.services.screening_service import ScreeningService, ScreeningSnapshotSummary, UniverseScreeningFilters
from src.services.settings_service import AppSettings, SettingsService
from src.services.ticker_ingestion_service import TickerIngestionService
from src.services.universe_discovery_service import UniverseDiscoveryService
from src.services.universe_service import UniverseService
from src.services.watchlist_service import AnalystMemo, CompanyAnalystDetail, WatchlistService
from src.ui.add_ticker_dialog import AddTickerDialog
from src.ui.backtesting_validation_dialog import BacktestingValidationDialog
from src.ui.company_detail_widget import CompanyDetailWidget
from src.ui.company_table_model import ScreenerRow
from src.ui.error_formatter import format_batch_summary, format_refresh_error
from src.ui.filter_widget import FilterWidget
from src.ui.screener_widget import ScreenerWidget
from src.ui.screening_snapshot_dialog import ScreeningSnapshotDialog
from src.ui.settings_dialog import SettingsDialog
from src.ui.universe_import_dialog import (
    MODE_DISCOVERY_ONLY,
    MODE_RESUME_LAST_FAILURES,
    UniverseImportDialog,
    UniverseImportOptions,
)
from src.ui.worker import Worker

WINDOW_TITLE = "Small Cap Screener"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
_FILTER_DOCK_WIDTH = 220
_STACK_SCREENER_INDEX = 0
_STACK_DETAIL_INDEX = 1


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._settings_service = SettingsService()
        self._settings = self._settings_service.load()
        self._maintenance_service = MaintenanceService()
        self._scoring_service = ScoringService(sub_score_weights=self._settings.scoring_weights())
        self._screening_service = ScreeningService(scoring_service=self._scoring_service)
        self._watchlist_service = WatchlistService()
        self._company_detail_service = CompanyDetailService()
        self._company_charts_service = CompanyChartsService()
        self._peer_comparison_service = PeerComparisonService()
        self._backtesting_service = BacktestingService(scoring_service=self._scoring_service)
        self._universe_service = UniverseService()
        self._financial_data_service = self._build_financial_data_service(self._settings)
        _kpi_snapshot_service = KpiSnapshotService(scoring_service=self._scoring_service)
        self._ticker_ingestion_service = TickerIngestionService(
            financial_data_service=self._financial_data_service,
            kpi_snapshot_service=_kpi_snapshot_service,
        )
        self._universe_discovery_service = UniverseDiscoveryService(
            financial_data_service=self._financial_data_service,
            kpi_snapshot_service=_kpi_snapshot_service,
        )
        self._current_filters = UniverseScreeningFilters()
        self._selected_company_id: int | None = None
        self._last_import_failed_company_ids: list[int] = []
        self._last_import_failed_tickers: list[str] = []
        self._active_workers: set[Worker] = set()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self._setup_ui()
        self._load_scored_universe()

    def _setup_ui(self) -> None:
        self._stack = QStackedWidget()

        self._screener = ScreenerWidget()
        self._detail = CompanyDetailWidget()

        self._stack.addWidget(self._screener)
        self._stack.addWidget(self._detail)
        self._stack.setCurrentIndex(_STACK_SCREENER_INDEX)

        self._screener.row_selected.connect(self._on_row_selected)
        self._screener.selection_cleared.connect(self._on_selection_cleared)
        self._detail.back_requested.connect(self._on_back_requested)
        self._detail.add_watchlist_requested.connect(self._on_add_watchlist_requested)
        self._detail.remove_watchlist_requested.connect(self._on_remove_watchlist_requested)
        self._detail.save_watchlist_requested.connect(self._on_save_watchlist_requested)
        self._detail.refresh_company_requested.connect(self._on_refresh_company_requested)

        self.setCentralWidget(self._stack)
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
        self._import_france_universe_action = QAction("Importer univers France…", self)
        self._import_france_universe_action.triggered.connect(self._open_import_france_dialog)
        file_menu.addAction(self._import_france_universe_action)
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
        file_menu.addAction("Validation ranking backtest…", self._open_backtesting_validation)
        file_menu.addSeparator()
        file_menu.addAction("Exporter CSV…", self._export_csv)
        file_menu.addAction("Exporter Excel…", self._export_excel)
        file_menu.addAction("Exporter watchlist CSV…", self._export_watchlist_csv)
        file_menu.addSeparator()
        file_menu.addAction("Paramètres…", self._open_settings_dialog)

        maintenance_menu = self.menuBar().addMenu("Maintenance")
        maintenance_menu.addAction("Sauvegarder la base de données…", self._backup_database)
        maintenance_menu.addAction("Nettoyer/Optimiser (VACUUM)", self._vacuum_database)
        maintenance_menu.addSeparator()
        maintenance_menu.addAction("Réinitialiser les données…", self._reset_demo_data)
        maintenance_menu.addAction("Afficher l'emplacement de la base", self._show_database_location)

    def _load_scored_universe(self, selected_company_id: int | None = None) -> None:
        rows = self._screening_service.filter_universe_with_scores(self._current_filters)
        self._screener.load(rows)
        if not rows:
            self._selected_company_id = None
            self._detail.clear()
            self._stack.setCurrentIndex(_STACK_SCREENER_INDEX)
            self.statusBar().showMessage("Aucune société ne correspond aux filtres.")
            return
        if selected_company_id is not None and self._screener.select_company(selected_company_id):
            self.statusBar().clearMessage()
            return
        self._selected_company_id = None
        self._detail.clear()
        self._stack.setCurrentIndex(_STACK_SCREENER_INDEX)
        self.statusBar().clearMessage()

    def _on_filters_applied(self, filters: UniverseScreeningFilters) -> None:
        self._current_filters = filters
        self._load_scored_universe(selected_company_id=self._selected_company_id)

    def _on_row_selected(self, row: ScreenerRow) -> None:
        self._selected_company_id = row.company_id
        analyst_detail = self._watchlist_service.get_company_analyst_detail(row.company_id)
        financial_detail = self._company_detail_service.get_financial_detail(row.company_id)
        score_breakdown = _score_breakdown_input(row, analyst_detail)
        chart_data = self._company_charts_service.build_company_charts_data(
            row.company_id,
            financial_detail=financial_detail,
            score_breakdown=score_breakdown,
        )
        peer_comparison = self._peer_comparison_service.get_company_peer_comparison(row.company_id)
        self._detail.load(row, analyst_detail, financial_detail, chart_data, peer_comparison)
        self._stack.setCurrentIndex(_STACK_DETAIL_INDEX)

    def _on_back_requested(self) -> None:
        self._stack.setCurrentIndex(_STACK_SCREENER_INDEX)

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

    def _open_import_france_dialog(self) -> None:
        dialog = UniverseImportDialog(can_resume=bool(self._last_import_failed_company_ids), parent=self)
        if dialog.exec() == 0 or dialog.options is None:
            return
        options = dialog.options
        if options.mode == MODE_RESUME_LAST_FAILURES:
            self._start_resume_last_failed_enrichment(options)
            return
        self._start_euronext_discovery(options)

    def _start_euronext_discovery(self, options: UniverseImportOptions) -> None:
        self._set_refresh_actions_enabled(False)
        self.statusBar().showMessage("Discovery Euronext France en cours…")

        worker = Worker(self._universe_service.import_euronext_france_universe)
        worker.signals.finished.connect(lambda result: self._on_euronext_discovery_finished(result, options, worker))
        worker.signals.error.connect(lambda exc: self._on_worker_error("Échec discovery Euronext", exc, worker))
        self._active_workers.add(worker)
        worker.start()

    def _on_euronext_discovery_finished(self, result, options: UniverseImportOptions, worker: Worker) -> None:
        self._active_workers.discard(worker)
        self._load_scored_universe(selected_company_id=self._selected_company_id)

        discovered = result.discovered_count
        upserted = result.upserted_count
        if options.mode == MODE_DISCOVERY_ONLY:
            self._set_refresh_actions_enabled(True)
            self.statusBar().showMessage(f"Discovery terminée: {discovered} société(s) détectée(s).", 7000)
            QMessageBox.information(
                self,
                "Importer univers France",
                (
                    "Discovery terminée.\n\n"
                    f"Sociétés découvertes: {discovered}\n"
                    f"Sociétés importées/mises à jour: {upserted}\n\n"
                    "Aucun enrichissement Yahoo n'a été lancé (mode discovery only)."
                ),
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirmer enrichissement massif",
            (
                "Discovery terminée.\n\n"
                f"Sociétés découvertes: {discovered}\n"
                f"Sociétés importées/mises à jour: {upserted}\n\n"
                "Lancer maintenant l'enrichissement Yahoo de ces sociétés ?\n"
                "Cette opération peut être longue et générer de nombreux appels fournisseur."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            self._set_refresh_actions_enabled(True)
            self.statusBar().showMessage("Discovery terminée. Enrichissement annulé.", 7000)
            return

        self._start_enrichment_for_company_ids(
            company_ids=result.upserted_company_ids,
            options=options,
            run_label="Import univers France",
            skip_recently_refreshed=False,
        )

    def _start_resume_last_failed_enrichment(self, options: UniverseImportOptions) -> None:
        if not self._last_import_failed_company_ids:
            QMessageBox.information(self, "Reprise enrichissement", "Aucun échec précédent à reprendre.")
            return
        confirm = QMessageBox.question(
            self,
            "Reprendre les échecs",
            (
                "Vous allez relancer l'enrichissement des échecs précédents.\n\n"
                f"Sociétés concernées: {len(self._last_import_failed_company_ids)}"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._start_enrichment_for_company_ids(
            company_ids=self._last_import_failed_company_ids,
            options=options,
            run_label="Reprise enrichissement",
            skip_recently_refreshed=True,
        )

    def _start_enrichment_for_company_ids(
        self,
        *,
        company_ids: list[int],
        options: UniverseImportOptions,
        run_label: str,
        skip_recently_refreshed: bool,
    ) -> None:
        if not company_ids:
            self._set_refresh_actions_enabled(True)
            QMessageBox.information(self, "Enrichissement", "Aucune société à enrichir.")
            return

        self._set_refresh_actions_enabled(False)
        self.statusBar().showMessage(f"{run_label} — préparation de l'enrichissement…")
        self._last_import_failed_company_ids = []
        self._last_import_failed_tickers = []

        worker = Worker(
            self._universe_discovery_service.refresh_companies_by_ids,
            company_id_list=company_ids,
            pacing_seconds=options.pacing_seconds,
            batch_size=options.batch_size,
            skip_recently_refreshed=skip_recently_refreshed,
        )
        worker.signals.progress.connect(lambda payload: self._on_universe_enrichment_progress(payload, run_label))
        worker.signals.finished.connect(lambda result: self._on_universe_enrichment_finished(result, run_label, worker))
        worker.signals.error.connect(lambda exc: self._on_worker_error("Échec enrichissement univers", exc, worker))
        self._active_workers.add(worker)
        worker.start()

    def _on_universe_enrichment_progress(self, payload: dict, run_label: str) -> None:
        phase = payload.get("phase")
        if phase == "batch_start":
            batch_number = payload.get("batch_number", 0)
            total_batches = payload.get("total_batches", 0)
            processed = payload.get("processed", 0)
            total = payload.get("total", 0)
            self.statusBar().showMessage(
                f"{run_label} — lot {batch_number}/{total_batches} (traitées: {processed}/{total})"
            )
            return
        if phase == "company_start":
            ticker = payload.get("ticker", "")
            processed = payload.get("processed", 0)
            total = payload.get("total", 0)
            self.statusBar().showMessage(f"{run_label} — {processed + 1}/{total} en cours: {ticker}")
            return
        if phase == "company_result":
            ticker = payload.get("ticker", "")
            processed = payload.get("processed", 0)
            total = payload.get("total", 0)
            status = payload.get("status")
            if status == "failed":
                self.statusBar().showMessage(f"{run_label} — {processed}/{total} échec: {ticker}")
            elif status == "skipped":
                self.statusBar().showMessage(f"{run_label} — {processed}/{total} ignoré: {ticker}")
            else:
                self.statusBar().showMessage(f"{run_label} — {processed}/{total} ok: {ticker}")

    def _on_universe_enrichment_finished(self, result, run_label: str, worker: Worker) -> None:
        self._active_workers.discard(worker)
        self._set_refresh_actions_enabled(True)
        self._load_scored_universe(selected_company_id=self._selected_company_id)

        failed_results = [entry for entry in result.results if not entry.success]
        self._last_import_failed_company_ids = [entry.company_id for entry in failed_results]
        self._last_import_failed_tickers = [entry.ticker for entry in failed_results if entry.ticker]

        failed_preview = ", ".join(self._last_import_failed_tickers[:10]) if self._last_import_failed_tickers else "—"
        skipped_preview = ", ".join(result.skipped_tickers[:10]) if result.skipped_tickers else "—"
        summary = (
            f"{run_label} terminé.\n\n"
            f"Total: {result.total}\n"
            f"Succès: {result.succeeded}\n"
            f"Échecs: {result.failed}\n"
            f"Ignorés: {result.skipped}\n"
            f"Tickers en échec: {failed_preview}\n"
            f"Tickers ignorés: {skipped_preview}"
        )
        if result.failed > 0:
            QMessageBox.warning(self, run_label, summary)
        else:
            QMessageBox.information(self, run_label, summary)
        self.statusBar().showMessage(
            (
                f"{run_label} — succès {result.succeeded}/{result.total}, "
                f"échecs {result.failed}, ignorés {result.skipped}."
            ),
            9000,
        )

    def _on_refresh_company_requested(self, company_id: int) -> None:
        self._set_refresh_actions_enabled(False)
        self.statusBar().showMessage("Actualisation en cours…")

        worker = Worker(self._universe_discovery_service.refresh_company, company_id)
        worker.signals.finished.connect(
            lambda result, cid=company_id: self._on_refresh_company_finished(result, cid, worker)
        )
        worker.signals.error.connect(lambda exc: self._on_worker_error("Actualisation échouée", exc, worker))
        self._active_workers.add(worker)
        worker.start()

    def _on_refresh_company_finished(self, result, company_id: int, worker: Worker) -> None:
        self._active_workers.discard(worker)
        self._set_refresh_actions_enabled(True)
        if not result.success:
            QMessageBox.warning(
                self,
                "Actualisation échouée",
                format_refresh_error(result.ticker, result.error_kind, result.stage),
            )
            self.statusBar().clearMessage()
            return
        self._load_scored_universe(selected_company_id=company_id)
        msg = f"{result.ticker} actualisé."
        if result.warnings:
            msg += f" Avertissements : {'; '.join(result.warnings)}"
        self.statusBar().showMessage(msg, 6000)

    def _refresh_universe(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Confirmer actualisation univers",
            ("Cette action va relancer l'actualisation de toutes les sociétés actives.\n" "Voulez-vous continuer ?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._set_refresh_actions_enabled(False)
        self.statusBar().showMessage("Actualisation de l'univers en cours…")

        worker = Worker(self._universe_discovery_service.batch_refresh_universe)
        worker.signals.finished.connect(lambda result: self._on_refresh_universe_finished(result, worker))
        worker.signals.error.connect(lambda exc: self._on_worker_error("Échec actualisation univers", exc, worker))
        self._active_workers.add(worker)
        worker.start()

    def _on_refresh_universe_finished(self, result, worker: Worker) -> None:
        self._active_workers.discard(worker)
        self._set_refresh_actions_enabled(True)
        self._load_scored_universe(selected_company_id=self._selected_company_id)
        failed_tickers = [r.ticker for r in result.results if not r.success]
        msg = format_batch_summary("Univers actualisé", result.succeeded, result.total, result.failed, failed_tickers)
        self.statusBar().showMessage(msg, 8000)

    def _refresh_watchlist(self) -> None:
        self._set_refresh_actions_enabled(False)
        self.statusBar().showMessage("Actualisation de la watchlist en cours…")

        worker = Worker(self._universe_discovery_service.refresh_watchlist)
        worker.signals.finished.connect(lambda result: self._on_refresh_watchlist_finished(result, worker))
        worker.signals.error.connect(lambda exc: self._on_worker_error("Échec actualisation watchlist", exc, worker))
        self._active_workers.add(worker)
        worker.start()

    def _on_refresh_watchlist_finished(self, result, worker: Worker) -> None:
        self._active_workers.discard(worker)
        self._set_refresh_actions_enabled(True)
        self._load_scored_universe(selected_company_id=self._selected_company_id)
        failed_tickers = [r.ticker for r in result.results if not r.success]
        msg = format_batch_summary(
            "Watchlist actualisée", result.succeeded, result.total, result.failed, failed_tickers
        )
        self.statusBar().showMessage(msg, 8000)

    def _on_worker_error(self, title: str, exc: Exception, worker: Worker) -> None:
        self._active_workers.discard(worker)
        self._set_refresh_actions_enabled(True)
        self.statusBar().clearMessage()
        QMessageBox.critical(self, title, f"Une erreur est survenue :\n{exc}")

    def _set_refresh_actions_enabled(self, enabled: bool) -> None:
        self._refresh_universe_action.setEnabled(enabled)
        self._refresh_watchlist_action.setEnabled(enabled)
        self._import_france_universe_action.setEnabled(enabled)
        self._detail._refresh_btn.setEnabled(enabled)
        if enabled:
            from PySide6.QtCore import Qt

            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            from PySide6.QtCore import Qt

            self.setCursor(Qt.CursorShape.WaitCursor)

    def _export_csv(self) -> None:
        rows = self._screener.rows()
        if not rows:
            QMessageBox.information(self, "Export", "Aucune donnée à exporter.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter CSV", "screening.csv", "CSV (*.csv)")
        if path:
            try:
                csv_content = self._screening_service.export_universe_with_scores_csv(
                    self._current_filters,
                )
                Path(path).write_text(csv_content, encoding="utf-8-sig")
            except OSError as exc:
                QMessageBox.warning(self, "Export", f"Échec export CSV: {exc}")
                return
            self.statusBar().showMessage(f"Export CSV réussi: {path}", 6000)

    def _export_excel(self) -> None:
        rows = self._screener.rows()
        if not rows:
            QMessageBox.information(self, "Export", "Aucune donnée à exporter.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter Excel", "screening.xlsx", "Excel (*.xlsx)")
        if path:
            try:
                excel_content = self._screening_service.export_universe_with_scores_excel(
                    self._current_filters,
                )
                Path(path).write_bytes(excel_content)
            except OSError as exc:
                QMessageBox.warning(self, "Export", f"Échec export Excel: {exc}")
                return
            self.statusBar().showMessage(f"Export Excel réussi: {path}", 6000)

    def _export_watchlist_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Exporter watchlist CSV", "watchlist.csv", "CSV (*.csv)")
        if path:
            try:
                csv_content = self._screening_service.export_watchlist_with_scores_csv(self._current_filters)
                Path(path).write_text(csv_content, encoding="utf-8-sig")
            except OSError as exc:
                QMessageBox.warning(self, "Export", f"Échec export watchlist CSV: {exc}")
                return
            self.statusBar().showMessage(f"Export watchlist CSV réussi: {path}", 6000)

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

    def _open_backtesting_validation(self) -> None:
        forward_days, accepted = QInputDialog.getInt(
            self,
            "Backtesting ranking",
            "Forward horizon (days)",
            90,
            1,
            3650,
            1,
        )
        if not accepted:
            return
        analysis = self._backtesting_service.analyze_ranking_validation(forward_days=forward_days)
        if analysis.total_snapshots == 0:
            QMessageBox.information(self, "Backtesting", "Aucun snapshot KPI disponible pour le backtest.")
            return
        dialog = BacktestingValidationDialog(analysis, parent=self)
        dialog.exec()

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self._settings_service, parent=self)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()

    def _on_settings_saved(self, settings: AppSettings) -> None:
        self._settings = settings
        self._financial_data_service.offline_mode = settings.offline_mode
        self._financial_data_service.provider_call_max_attempts = settings.provider_retry_attempts
        self._scoring_service.sub_score_weights = settings.scoring_weights()
        self._load_scored_universe(selected_company_id=self._selected_company_id)
        self.statusBar().showMessage("Paramètres appliqués.", 4000)

    def _backup_database(self) -> None:
        try:
            backup_path = self._maintenance_service.backup_database()
            QMessageBox.information(
                self,
                "Sauvegarde réussie",
                f"Base de données sauvegardée dans :\n{backup_path.resolve()}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur de sauvegarde", f"Impossible de sauvegarder la base de données :\n{e}")

    def _vacuum_database(self) -> None:
        try:
            self._maintenance_service.vacuum_database()
            QMessageBox.information(
                self,
                "Optimisation terminée",
                "La base de données a été nettoyée et optimisée avec succès.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'optimiser la base de données :\n{e}")

    def _reset_demo_data(self) -> None:
        reply = QMessageBox.question(
            self,
            "Réinitialisation",
            "Attention : cette action supprimera TOUTES les données en base "
            "(entreprises, ratios, watchlists, etc.).\n\nVoulez-vous continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._maintenance_service.reset_demo_data()
                self._load_scored_universe()
                QMessageBox.information(self, "Réinitialisation", "Toutes les données ont été effacées avec succès.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de réinitialiser la base :\n{e}")

    def _show_database_location(self) -> None:
        path = self._maintenance_service.get_database_path()
        if path is not None:
            QMessageBox.information(self, "Emplacement", f"La base de données se trouve ici :\n{path.resolve()}")
        else:
            QMessageBox.warning(self, "Emplacement", "Emplacement indisponible (la base n'est peut-être pas locale).")

    @staticmethod
    def _build_financial_data_service(settings: AppSettings) -> FinancialDataService:
        return FinancialDataService(
            provider=YFinanceProvider(),
            offline_mode=settings.offline_mode,
            provider_call_max_attempts=settings.provider_retry_attempts,
        )


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


def _score_breakdown_input(row: ScreenerRow, analyst_detail: CompanyAnalystDetail | None) -> ScoreBreakdownInput:
    quality = row.quality_score
    value = row.value_score
    growth = row.growth_score
    risk = row.risk_score
    if analyst_detail is not None:
        quality = analyst_detail.quality_score
        value = analyst_detail.value_score
        growth = analyst_detail.growth_score
        risk = analyst_detail.risk_score
    return ScoreBreakdownInput(
        quality=quality,
        value=value,
        growth=growth,
        risk=risk,
    )
