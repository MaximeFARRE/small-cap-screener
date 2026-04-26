from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

import src.ui.main_window as main_window_module
from src.services.screening_service import (
    ScreeningSnapshotComparisonRow,
    ScreeningSnapshotRow,
    ScreeningSnapshotSummary,
    ScreeningSnapshotView,
    UniverseScreeningFilters,
)


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class FakeScreeningService:
    def __init__(self) -> None:
        self.filter_calls: list[UniverseScreeningFilters] = []
        self.save_calls: list[tuple[UniverseScreeningFilters, str]] = []
        self.view_calls: list[int] = []
        self.compare_calls: list[tuple[int, UniverseScreeningFilters]] = []
        self.recent_summaries: list[ScreeningSnapshotSummary] = []
        self.snapshot_view: ScreeningSnapshotView | None = None
        self.comparison_rows: list[ScreeningSnapshotComparisonRow] = []

    def filter_universe_with_scores(self, filters: UniverseScreeningFilters):
        self.filter_calls.append(filters)
        return []

    def save_screening_snapshot(self, filters: UniverseScreeningFilters, *, name: str, **_kwargs):
        self.save_calls.append((filters, name))
        return SimpleNamespace(snapshot_id=7, company_count=3)

    def list_recent_screening_snapshots(self, limit: int = 20) -> list[ScreeningSnapshotSummary]:
        return self.recent_summaries[:limit]

    def get_screening_snapshot_view(self, snapshot_id: int) -> ScreeningSnapshotView | None:
        self.view_calls.append(snapshot_id)
        return self.snapshot_view

    def compare_snapshot_to_current(
        self,
        snapshot_id: int,
        current_filters: UniverseScreeningFilters,
        **_kwargs,
    ) -> list[ScreeningSnapshotComparisonRow]:
        self.compare_calls.append((snapshot_id, current_filters))
        return self.comparison_rows


class FakeWatchlistService:
    def get_company_analyst_detail(self, _company_id: int):
        return None


class FakeCompanyDetailService:
    def get_financial_detail(self, _company_id: int):
        return None


class FakeCompanyChartsService:
    def get_company_charts_data(self, _company_id: int):
        return None

    def build_company_charts_data(self, _company_id: int, **_kwargs):
        return None


class FakeFinancialDataService:
    def __init__(self, **_kwargs) -> None:
        pass


class FakeKpiSnapshotService:
    def __init__(self, **_kwargs) -> None:
        pass


class FakeTickerIngestionService:
    def __init__(self, **_kwargs) -> None:
        pass


class FakeUniverseDiscoveryService:
    def __init__(self, **_kwargs) -> None:
        pass


class FakeSnapshotDialog:
    last_instance = None

    def __init__(self, snapshot_view, comparison_rows, parent=None) -> None:
        self.snapshot_view = snapshot_view
        self.comparison_rows = comparison_rows
        self.parent = parent
        self.exec_called = False
        FakeSnapshotDialog.last_instance = self

    def exec(self) -> int:
        self.exec_called = True
        return 1


def _build_window(monkeypatch, qapp):
    monkeypatch.setattr(main_window_module, "ScreeningService", FakeScreeningService)
    monkeypatch.setattr(main_window_module, "WatchlistService", FakeWatchlistService)
    monkeypatch.setattr(main_window_module, "CompanyDetailService", FakeCompanyDetailService)
    monkeypatch.setattr(main_window_module, "CompanyChartsService", FakeCompanyChartsService)
    monkeypatch.setattr(main_window_module, "FinancialDataService", FakeFinancialDataService)
    monkeypatch.setattr(main_window_module, "KpiSnapshotService", FakeKpiSnapshotService)
    monkeypatch.setattr(main_window_module, "TickerIngestionService", FakeTickerIngestionService)
    monkeypatch.setattr(main_window_module, "UniverseDiscoveryService", FakeUniverseDiscoveryService)
    monkeypatch.setattr(main_window_module, "YFinanceProvider", lambda: object())
    monkeypatch.setattr(main_window_module.QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", lambda *args, **kwargs: None)
    return main_window_module.MainWindow()


def test_save_screening_snapshot_uses_current_filters(monkeypatch, qapp):
    window = _build_window(monkeypatch, qapp)
    window._current_filters = UniverseScreeningFilters(sector="Tech", sort_by="ticker", descending=True)
    monkeypatch.setattr(
        main_window_module.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: ("snapshot tech", True)),
    )

    window._save_screening_snapshot()

    save_calls = window._screening_service.save_calls
    assert len(save_calls) == 1
    saved_filters, saved_name = save_calls[0]
    assert saved_filters.sector == "Tech"
    assert saved_filters.sort_by == "ticker"
    assert saved_filters.descending is True
    assert saved_name == "snapshot tech"


def test_open_recent_screening_snapshots_loads_view_and_comparison(monkeypatch, qapp):
    window = _build_window(monkeypatch, qapp)
    summary = ScreeningSnapshotSummary(
        snapshot_id=11,
        name="snapshot recent",
        created_at=main_window_module.datetime(2026, 4, 26, 18, 0),
        company_count=1,
        filters={"sort_by": "rank"},
        filters_summary="sort=rank asc",
    )
    window._screening_service.recent_summaries = [summary]
    window._screening_service.snapshot_view = ScreeningSnapshotView(
        summary=summary,
        rows=[
            ScreeningSnapshotRow(
                company_id=1,
                ticker="ALP.PA",
                name="Alpha",
                sector="Tech",
                total_score=80.0,
                quality_score=70.0,
                value_score=75.0,
                growth_score=78.0,
                risk_score=65.0,
                rank=1,
                sector_rank=1,
            )
        ],
    )
    window._screening_service.comparison_rows = [
        ScreeningSnapshotComparisonRow(
            company_id=1,
            ticker="ALP.PA",
            name="Alpha",
            sector="Tech",
            snapshot_rank=2,
            current_rank=1,
            rank_change=1,
            snapshot_total_score=78.0,
            current_total_score=80.0,
            total_score_change=2.0,
        )
    ]
    monkeypatch.setattr(
        main_window_module.QInputDialog,
        "getItem",
        staticmethod(lambda *args, **kwargs: (main_window_module._snapshot_summary_option(summary), True)),
    )
    monkeypatch.setattr(main_window_module, "ScreeningSnapshotDialog", FakeSnapshotDialog)

    window._open_recent_screening_snapshots()

    assert window._screening_service.view_calls == [11]
    assert len(window._screening_service.compare_calls) == 1
    compared_snapshot_id, compared_filters = window._screening_service.compare_calls[0]
    assert compared_snapshot_id == 11
    assert compared_filters == window._current_filters
    assert FakeSnapshotDialog.last_instance is not None
    assert FakeSnapshotDialog.last_instance.exec_called is True
