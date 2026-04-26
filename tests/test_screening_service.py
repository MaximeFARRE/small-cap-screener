import csv
import io
import zipfile
from contextlib import contextmanager
from datetime import UTC, date, datetime
from xml.etree import ElementTree

import pytest

from src.models.company import Company
from src.models.kpi_snapshot import KpiSnapshot
from src.models.watchlist_entry import (
    WATCHLIST_STATUS_CONVICTION,
    WATCHLIST_STATUS_REVIEW,
    WATCHLIST_STATUS_WATCHING,
    WatchlistEntry,
)
from src.repositories import company_repository, kpi_snapshot_repository, watchlist_repository
from src.services.ratio_service import CompanyRatios
from src.services.screening_service import (
    ScreeningCriteria,
    ScreeningService,
    UniverseScreeningFilters,
    apply_filters,
)

_CSV_HEADERS = [
    "ticker",
    "name",
    "sector",
    "total_score",
    "quality_score",
    "value_score",
    "growth_score",
    "risk_score",
    "rank",
    "sector_rank",
]
_XLSX_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _make_ratios(company_id: int, **kwargs) -> CompanyRatios:
    defaults = dict(
        fiscal_year=2023,
        price=20.0,
        mkt_cap=10_000_000.0,
        ev=12_000_000.0,
        pe_ratio=12.0,
        pb_ratio=1.2,
        ev_ebitda=7.0,
        roe=0.12,
        net_margin=0.08,
        ebit_margin=0.10,
        debt_to_equity=0.4,
        net_debt_to_ebitda=1.5,
    )
    return CompanyRatios(company_id=company_id, **{**defaults, **kwargs})


def test_no_criteria_returns_all_sorted_by_score():
    candidates = [_make_ratios(1), _make_ratios(2), _make_ratios(3)]
    results = apply_filters(candidates, ScreeningCriteria())
    assert len(results) == 3


def test_results_sorted_by_score_descending():
    cheap = _make_ratios(1, pe_ratio=8.0, roe=0.20)
    expensive = _make_ratios(2, pe_ratio=22.0, roe=0.03)
    results = apply_filters([expensive, cheap], ScreeningCriteria())
    assert results[0].ratios.company_id == 1


def test_max_pe_filter_excludes_above_threshold():
    results = apply_filters(
        [_make_ratios(1, pe_ratio=10.0), _make_ratios(2, pe_ratio=20.0)],
        ScreeningCriteria(max_pe=15.0),
    )
    assert len(results) == 1
    assert results[0].ratios.company_id == 1


def test_min_roe_filter_excludes_below_threshold():
    results = apply_filters(
        [_make_ratios(1, roe=0.20), _make_ratios(2, roe=0.05)],
        ScreeningCriteria(min_roe=0.10),
    )
    assert len(results) == 1
    assert results[0].ratios.company_id == 1


def test_multiple_criteria_applied_together():
    results = apply_filters(
        [
            _make_ratios(1, pe_ratio=10.0, roe=0.18, net_debt_to_ebitda=1.0),
            _make_ratios(2, pe_ratio=10.0, roe=0.18, net_debt_to_ebitda=5.0),
        ],
        ScreeningCriteria(max_pe=15.0, min_roe=0.10, max_net_debt_to_ebitda=3.0),
    )
    assert len(results) == 1
    assert results[0].ratios.company_id == 1


def test_none_ratio_value_is_not_filtered_out():
    results = apply_filters(
        [_make_ratios(1, pe_ratio=None)],
        ScreeningCriteria(max_pe=15.0),
    )
    assert len(results) == 1


def test_empty_candidates_returns_empty():
    assert apply_filters([], ScreeningCriteria(max_pe=15.0)) == []


def test_result_contains_score():
    results = apply_filters([_make_ratios(1)], ScreeningCriteria())
    assert 0.0 <= results[0].score <= 100.0


def _make_screening_service(db_session) -> ScreeningService:
    @contextmanager
    def session_scope():
        yield db_session

    return ScreeningService(session_scope_factory=session_scope)


def _make_company(
    db_session,
    *,
    isin: str,
    ticker: str,
    name: str,
    sector: str | None,
    market_cap: float = 200_000_000.0,
) -> Company:
    return company_repository.create(
        db_session,
        Company(
            isin=isin,
            ticker=ticker,
            name=name,
            country="France",
            sector=sector,
            currency="EUR",
            is_active=True,
            market_cap=market_cap,
            average_daily_volume=150_000.0,
        ),
    )


def test_list_universe_with_scores_returns_ranked_rows(db_session):
    alpha = _make_company(
        db_session,
        isin="FR0000900001",
        ticker="ALP.PA",
        name="Alpha",
        sector="Energy",
    )
    beta = _make_company(
        db_session,
        isin="FR0000900002",
        ticker="BET.PA",
        name="Beta",
        sector="Tech",
    )
    gamma = _make_company(
        db_session,
        isin="FR0000900003",
        ticker="GAM.PA",
        name="Gamma",
        sector="Energy",
    )
    delta = _make_company(
        db_session,
        isin="FR0000900004",
        ticker="DEL.PA",
        name="Delta",
        sector="Industrial",
    )

    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=alpha.id,
            snapshot_date=date(2024, 10, 31),
            metrics={
                "total_score": 92.0,
                "quality_score": 90.0,
                "value_score": 88.0,
                "growth_score": 85.0,
                "risk_score": 80.0,
            },
            source="s1",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=beta.id,
            snapshot_date=date(2024, 10, 31),
            metrics={
                "total_score": 75.0,
                "quality_score": 70.0,
                "value_score": 72.0,
                "growth_score": 68.0,
                "risk_score": 74.0,
            },
            source="s1",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=gamma.id,
            snapshot_date=date(2024, 10, 31),
            metrics={
                "quality_score": 61.0,
                "value_score": 55.0,
                "growth_score": 58.0,
                "risk_score": 60.0,
            },
            source="s1",
        ),
    )

    service = _make_screening_service(db_session)
    rows = service.list_universe_with_scores()
    by_company_id = {row.company_id: row for row in rows}

    assert [row.company_id for row in rows] == [alpha.id, beta.id, gamma.id, delta.id]

    alpha_row = by_company_id[alpha.id]
    assert alpha_row.ticker == "ALP.PA"
    assert alpha_row.name == "Alpha"
    assert alpha_row.sector == "Energy"
    assert alpha_row.total_score == 92.0
    assert alpha_row.quality_score == 90.0
    assert alpha_row.value_score == 88.0
    assert alpha_row.growth_score == 85.0
    assert alpha_row.risk_score == 80.0
    assert alpha_row.rank == 1
    assert alpha_row.sector_rank == 1

    beta_row = by_company_id[beta.id]
    assert beta_row.total_score == 75.0
    assert beta_row.rank == 2
    assert beta_row.sector_rank == 1

    gamma_row = by_company_id[gamma.id]
    assert gamma_row.total_score is None
    assert gamma_row.quality_score == 61.0
    assert gamma_row.value_score == 55.0
    assert gamma_row.growth_score == 58.0
    assert gamma_row.risk_score == 60.0
    assert gamma_row.rank is None
    assert gamma_row.sector_rank is None

    delta_row = by_company_id[delta.id]
    assert delta_row.total_score is None
    assert delta_row.quality_score is None
    assert delta_row.value_score is None
    assert delta_row.growth_score is None
    assert delta_row.risk_score is None
    assert delta_row.rank is None
    assert delta_row.sector_rank is None


def _seed_scored_universe_for_filters(db_session) -> dict[str, Company]:
    alpha = _make_company(
        db_session,
        isin="FR0000910001",
        ticker="ALP.PA",
        name="Alpha",
        sector="Energy",
    )
    beta = _make_company(
        db_session,
        isin="FR0000910002",
        ticker="BET.PA",
        name="Beta",
        sector="Tech",
    )
    epsilon = _make_company(
        db_session,
        isin="FR0000910003",
        ticker="EPS.PA",
        name="Epsilon",
        sector="Energy",
    )
    gamma = _make_company(
        db_session,
        isin="FR0000910004",
        ticker="GAM.PA",
        name="Gamma",
        sector="Energy",
    )
    delta = _make_company(
        db_session,
        isin="FR0000910005",
        ticker="DEL.PA",
        name="Delta",
        sector="Industrial",
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=alpha.id,
            snapshot_date=date(2024, 11, 30),
            metrics={"total_score": 92.0},
            source="seed",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=beta.id,
            snapshot_date=date(2024, 11, 30),
            metrics={"total_score": 80.0},
            source="seed",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=epsilon.id,
            snapshot_date=date(2024, 11, 30),
            metrics={"total_score": 70.0},
            source="seed",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=gamma.id,
            snapshot_date=date(2024, 11, 30),
            metrics={"quality_score": 64.0},
            source="seed",
        ),
    )
    return {
        "alpha": alpha,
        "beta": beta,
        "epsilon": epsilon,
        "gamma": gamma,
        "delta": delta,
    }


def test_filter_universe_with_scores_by_sector(db_session):
    companies = _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(sector="  energy  "),
    )

    assert [row.company_id for row in rows] == [
        companies["alpha"].id,
        companies["epsilon"].id,
        companies["gamma"].id,
    ]


def test_filter_universe_with_scores_by_min_total_score(db_session):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(min_total_score=85.0),
    )

    assert [row.ticker for row in rows] == ["ALP.PA"]


def test_filter_universe_with_scores_scored_only(db_session):
    companies = _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(scored_only=True),
    )

    assert [row.company_id for row in rows] == [
        companies["alpha"].id,
        companies["beta"].id,
        companies["epsilon"].id,
    ]


def test_filter_universe_with_scores_watchlist_only(db_session):
    companies = _seed_scored_universe_for_filters(db_session)
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=companies["alpha"].id, status=WATCHLIST_STATUS_WATCHING),
    )
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=companies["gamma"].id, status=WATCHLIST_STATUS_REVIEW),
    )
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(watchlist_scope="watchlist_only", include_excluded=True),
    )

    assert [row.company_id for row in rows] == [companies["alpha"].id, companies["gamma"].id]


def test_filter_universe_with_scores_non_watchlist_only(db_session):
    companies = _seed_scored_universe_for_filters(db_session)
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=companies["beta"].id, status=WATCHLIST_STATUS_CONVICTION),
    )
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(watchlist_scope="non_watchlist_only"),
    )

    assert companies["beta"].id not in [row.company_id for row in rows]
    assert len(rows) == 4


def test_filter_universe_with_scores_by_watchlist_status(db_session):
    companies = _seed_scored_universe_for_filters(db_session)
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=companies["alpha"].id, status=WATCHLIST_STATUS_WATCHING),
    )
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=companies["beta"].id, status=WATCHLIST_STATUS_REVIEW),
    )
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(watchlist_status=WATCHLIST_STATUS_REVIEW, include_excluded=True),
    )

    assert [row.company_id for row in rows] == [companies["beta"].id]


def test_filter_universe_with_scores_exclusion_filter_modes(db_session):
    companies = _seed_scored_universe_for_filters(db_session)
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=companies["alpha"].id, is_excluded=True, status=WATCHLIST_STATUS_REVIEW),
    )
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=companies["beta"].id, is_excluded=False, status=WATCHLIST_STATUS_WATCHING),
    )
    service = _make_screening_service(db_session)

    excluded_only = service.filter_universe_with_scores(
        UniverseScreeningFilters(exclusion_filter="excluded_only", include_excluded=True),
    )
    non_excluded_only = service.filter_universe_with_scores(
        UniverseScreeningFilters(exclusion_filter="non_excluded_only"),
    )

    assert [row.company_id for row in excluded_only] == [companies["alpha"].id]
    assert companies["alpha"].id not in [row.company_id for row in non_excluded_only]


def test_filter_universe_with_scores_excludes_analyst_excluded_companies_by_default(db_session):
    companies = _seed_scored_universe_for_filters(db_session)
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=companies["beta"].id, is_excluded=True),
    )
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(UniverseScreeningFilters())

    assert companies["beta"].id not in [row.company_id for row in rows]


def test_filter_universe_with_scores_include_excluded_true_keeps_excluded_companies(db_session):
    companies = _seed_scored_universe_for_filters(db_session)
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=companies["beta"].id, is_excluded=True),
    )
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(include_excluded=True),
    )

    assert companies["beta"].id in [row.company_id for row in rows]


def test_filter_universe_with_scores_top_n(db_session):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(top_n=2),
    )

    assert [row.ticker for row in rows] == ["ALP.PA", "BET.PA"]


def test_filter_universe_with_scores_top_n_zero_returns_empty(db_session):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(top_n=0),
    )

    assert rows == []


def test_filter_universe_with_scores_combines_filters(db_session):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(
            sector="Energy",
            min_total_score=75.0,
            scored_only=True,
            top_n=5,
        ),
    )

    assert [row.ticker for row in rows] == ["ALP.PA"]


def test_filter_universe_with_scores_orders_by_rank_then_ticker(db_session):
    companies = _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(UniverseScreeningFilters())

    assert [row.company_id for row in rows] == [
        companies["alpha"].id,
        companies["beta"].id,
        companies["epsilon"].id,
        companies["delta"].id,
        companies["gamma"].id,
    ]


def test_filter_universe_with_scores_sort_by_total_score_descending(db_session):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(sort_by="total_score", descending=True),
    )

    assert [row.ticker for row in rows] == [
        "ALP.PA",
        "BET.PA",
        "EPS.PA",
        "DEL.PA",
        "GAM.PA",
    ]


def test_filter_universe_with_scores_sort_by_total_score_ascending(db_session):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(sort_by="total_score", descending=False),
    )

    assert [row.ticker for row in rows] == [
        "EPS.PA",
        "BET.PA",
        "ALP.PA",
        "DEL.PA",
        "GAM.PA",
    ]


def test_filter_universe_with_scores_sort_by_rank_descending(db_session):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(sort_by="rank", descending=True),
    )

    assert [row.ticker for row in rows] == [
        "EPS.PA",
        "BET.PA",
        "ALP.PA",
        "DEL.PA",
        "GAM.PA",
    ]


def test_filter_universe_with_scores_sort_by_ticker_descending(db_session):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(sort_by="ticker", descending=True),
    )

    assert [row.ticker for row in rows] == [
        "GAM.PA",
        "EPS.PA",
        "DEL.PA",
        "BET.PA",
        "ALP.PA",
    ]


@pytest.mark.parametrize(
    ("sort_by", "expected_tickers"),
    [
        ("quality_score", ["GAM.PA", "ALP.PA", "BET.PA", "DEL.PA", "EPS.PA"]),
        ("value_score", ["ALP.PA", "BET.PA", "DEL.PA", "EPS.PA", "GAM.PA"]),
        ("growth_score", ["ALP.PA", "BET.PA", "DEL.PA", "EPS.PA", "GAM.PA"]),
        ("risk_score", ["ALP.PA", "BET.PA", "DEL.PA", "EPS.PA", "GAM.PA"]),
    ],
)
def test_filter_universe_with_scores_sort_by_sub_scores_handles_none_values(
    db_session,
    sort_by: str,
    expected_tickers: list[str],
):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(sort_by=sort_by, descending=True),
    )

    assert [row.ticker for row in rows] == expected_tickers


def test_filter_universe_with_scores_uses_ticker_fallback_for_equal_primary_value(db_session):
    zeta = _make_company(
        db_session,
        isin="FR0000920001",
        ticker="ZZZ.PA",
        name="Zeta",
        sector="Tech",
    )
    alpha = _make_company(
        db_session,
        isin="FR0000920002",
        ticker="AAA.PA",
        name="Alpha tie",
        sector="Tech",
    )

    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=zeta.id,
            snapshot_date=date(2024, 12, 31),
            metrics={"total_score": 80.0},
            source="tie",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=alpha.id,
            snapshot_date=date(2024, 12, 31),
            metrics={"total_score": 80.0},
            source="tie",
        ),
    )

    service = _make_screening_service(db_session)
    rows = service.filter_universe_with_scores(
        UniverseScreeningFilters(sort_by="total_score", descending=True),
    )

    assert [row.ticker for row in rows] == ["AAA.PA", "ZZZ.PA"]


def _read_csv_rows(content: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def _xlsx_column_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha())
    index = 0
    for letter in letters:
        index = (index * 26) + (ord(letter.upper()) - ord("A") + 1)
    return max(index - 1, 0)


def _read_xlsx_rows(content: bytes) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_strings_root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in shared_strings_root.findall("m:si", _XLSX_NS):
                text_parts = [(node.text or "") for node in item.findall(".//m:t", _XLSX_NS)]
                shared_strings.append("".join(text_parts))

        sheet_root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    indexed_rows: list[dict[int, str]] = []
    for row in sheet_root.findall(".//m:sheetData/m:row", _XLSX_NS):
        indexed_values: dict[int, str] = {}
        for cell in row.findall("m:c", _XLSX_NS):
            column_index = _xlsx_column_index(cell.attrib.get("r", "A1"))
            cell_type = cell.attrib.get("t")
            if cell_type == "s":
                raw_index = cell.findtext("m:v", default="", namespaces=_XLSX_NS)
                if raw_index:
                    shared_index = int(raw_index)
                    value = shared_strings[shared_index] if shared_index < len(shared_strings) else ""
                else:
                    value = ""
            elif cell_type == "inlineStr":
                text_nodes = cell.findall("m:is//m:t", _XLSX_NS)
                value = "".join(node.text or "" for node in text_nodes)
            else:
                value = cell.findtext("m:v", default="", namespaces=_XLSX_NS)
            indexed_values[column_index] = value
        indexed_rows.append(indexed_values)

    if not indexed_rows:
        return []

    header_row = indexed_rows[0]
    ordered_columns = sorted(header_row.keys())
    headers = [header_row.get(column, "") for column in ordered_columns]

    output: list[dict[str, str]] = []
    for row in indexed_rows[1:]:
        output.append({header: row.get(column, "") for column, header in zip(ordered_columns, headers, strict=False)})
    return output


def test_export_universe_with_scores_csv_uses_filtered_sorted_order(db_session):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    content = service.export_universe_with_scores_csv(
        UniverseScreeningFilters(sort_by="ticker", descending=True, top_n=3),
    )
    rows = _read_csv_rows(content)

    assert content.splitlines()[0] == ",".join(_CSV_HEADERS)
    assert [row["ticker"] for row in rows] == ["GAM.PA", "EPS.PA", "DEL.PA"]


def test_export_universe_with_scores_csv_serializes_none_as_empty(db_session):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    content = service.export_universe_with_scores_csv(
        UniverseScreeningFilters(sort_by="total_score", descending=True),
    )
    rows = _read_csv_rows(content)
    by_ticker = {row["ticker"]: row for row in rows}

    assert by_ticker["DEL.PA"]["total_score"] == ""
    assert by_ticker["DEL.PA"]["quality_score"] == ""
    assert by_ticker["DEL.PA"]["rank"] == ""
    assert by_ticker["GAM.PA"]["total_score"] == ""
    assert by_ticker["GAM.PA"]["quality_score"] == "64.0"


def test_export_universe_with_scores_excel_uses_filtered_sorted_order(db_session):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    content = service.export_universe_with_scores_excel(
        UniverseScreeningFilters(sort_by="ticker", descending=True, top_n=3),
    )
    rows = _read_xlsx_rows(content)

    assert list(rows[0].keys()) == _CSV_HEADERS
    assert [row["ticker"] for row in rows] == ["GAM.PA", "EPS.PA", "DEL.PA"]


def test_export_universe_with_scores_excel_serializes_none_as_empty(db_session):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)

    content = service.export_universe_with_scores_excel(
        UniverseScreeningFilters(sort_by="total_score", descending=True),
    )
    rows = _read_xlsx_rows(content)
    by_ticker = {row["ticker"]: row for row in rows}

    assert by_ticker["DEL.PA"]["total_score"] == ""
    assert by_ticker["DEL.PA"]["quality_score"] == ""
    assert by_ticker["DEL.PA"]["rank"] == ""
    assert by_ticker["GAM.PA"]["total_score"] == ""
    assert float(by_ticker["GAM.PA"]["quality_score"]) == pytest.approx(64.0)


def test_export_universe_with_scores_excel_excludes_excluded_companies_by_default(db_session):
    companies = _seed_scored_universe_for_filters(db_session)
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=companies["beta"].id, is_excluded=True),
    )
    service = _make_screening_service(db_session)

    content = service.export_universe_with_scores_excel(UniverseScreeningFilters())
    rows = _read_xlsx_rows(content)
    default_tickers = [row["ticker"] for row in rows]

    assert "BET.PA" not in default_tickers

    content_with_excluded = service.export_universe_with_scores_excel(
        UniverseScreeningFilters(include_excluded=True),
    )
    rows_with_excluded = _read_xlsx_rows(content_with_excluded)
    included_tickers = [row["ticker"] for row in rows_with_excluded]

    assert "BET.PA" in included_tickers


def test_save_and_get_screening_snapshot_roundtrip(db_session):
    companies = _seed_scored_universe_for_filters(db_session)
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=companies["beta"].id, is_excluded=True),
    )
    service = _make_screening_service(db_session)

    saved = service.save_screening_snapshot(
        UniverseScreeningFilters(sort_by="ticker", descending=True),
        name="snapshot one",
    )
    loaded = service.get_screening_snapshot(saved.snapshot_id)

    assert loaded is not None
    assert loaded.snapshot_id == saved.snapshot_id
    assert loaded.name == "snapshot one"
    assert loaded.filters["sort_by"] == "ticker"
    assert loaded.filters["descending"] is True
    assert loaded.filters["include_excluded"] is False
    assert loaded.company_count == 4
    assert loaded.company_ids == [
        companies["gamma"].id,
        companies["epsilon"].id,
        companies["delta"].id,
        companies["alpha"].id,
    ]
    assert [row["ticker"] for row in loaded.results] == ["GAM.PA", "EPS.PA", "DEL.PA", "ALP.PA"]


def test_save_screening_snapshot_can_include_excluded_companies(db_session):
    companies = _seed_scored_universe_for_filters(db_session)
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=companies["beta"].id, is_excluded=True),
    )
    service = _make_screening_service(db_session)

    saved = service.save_screening_snapshot(
        UniverseScreeningFilters(include_excluded=True, sort_by="rank"),
        name="snapshot include excluded",
    )

    assert saved.company_count == 5
    assert companies["beta"].id in saved.company_ids
    assert "BET.PA" in [row["ticker"] for row in saved.results]


def test_get_screening_snapshot_returns_none_when_missing(db_session):
    service = _make_screening_service(db_session)

    loaded = service.get_screening_snapshot(999999)

    assert loaded is None


def test_list_recent_screening_snapshots_returns_summary_view(db_session):
    _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)
    first = service.save_screening_snapshot(
        UniverseScreeningFilters(sector="Energy", sort_by="rank"),
        name="energy screen",
    )
    second = service.save_screening_snapshot(
        UniverseScreeningFilters(watchlist_scope="watchlist_only", sort_by="ticker", descending=True),
        name="watchlist screen",
    )

    listed = service.list_recent_screening_snapshots(limit=10)

    assert [snapshot.snapshot_id for snapshot in listed[:2]] == [second.snapshot_id, first.snapshot_id]
    assert listed[0].name == "watchlist screen"
    assert listed[0].company_count == second.company_count
    assert "watchlist=watchlist_only" in listed[0].filters_summary
    assert "sort=ticker desc" in listed[0].filters_summary


def test_get_screening_snapshot_view_returns_rows_with_company_ids(db_session):
    companies = _seed_scored_universe_for_filters(db_session)
    service = _make_screening_service(db_session)
    saved = service.save_screening_snapshot(
        UniverseScreeningFilters(sort_by="ticker", descending=True),
        name="view snapshot",
    )

    view = service.get_screening_snapshot_view(saved.snapshot_id)

    assert view is not None
    assert view.summary.snapshot_id == saved.snapshot_id
    assert view.summary.company_count == 5
    assert [row.company_id for row in view.rows] == [
        companies["gamma"].id,
        companies["epsilon"].id,
        companies["delta"].id,
        companies["beta"].id,
        companies["alpha"].id,
    ]
    assert [row.ticker for row in view.rows] == ["GAM.PA", "EPS.PA", "DEL.PA", "BET.PA", "ALP.PA"]


def test_compare_snapshot_to_current_returns_rank_and_score_changes(db_session):
    alpha = _make_company(
        db_session,
        isin="FR0000990001",
        ticker="ALP.PA",
        name="Alpha",
        sector="Energy",
    )
    beta = _make_company(
        db_session,
        isin="FR0000990002",
        ticker="BET.PA",
        name="Beta",
        sector="Tech",
    )
    gamma = _make_company(
        db_session,
        isin="FR0000990003",
        ticker="GAM.PA",
        name="Gamma",
        sector="Industrial",
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=alpha.id,
            snapshot_date=date(2025, 1, 1),
            metrics={"total_score": 70.0},
            source="before",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=beta.id,
            snapshot_date=date(2025, 1, 1),
            metrics={"total_score": 90.0},
            source="before",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=gamma.id,
            snapshot_date=date(2025, 1, 1),
            metrics={"total_score": 60.0},
            source="before",
        ),
    )
    service = _make_screening_service(db_session)
    saved = service.save_screening_snapshot(
        UniverseScreeningFilters(sort_by="rank"),
        name="baseline snapshot",
    )

    updated_alpha = kpi_snapshot_repository.get_latest_by_company(db_session, alpha.id)
    updated_beta = kpi_snapshot_repository.get_latest_by_company(db_session, beta.id)
    updated_gamma = kpi_snapshot_repository.get_latest_by_company(db_session, gamma.id)
    assert updated_alpha is not None
    assert updated_beta is not None
    assert updated_gamma is not None
    updated_alpha.metrics = {"total_score": 95.0}
    updated_beta.metrics = {"total_score": 80.0}
    updated_gamma.metrics = {"total_score": 50.0}
    db_session.flush()

    compared = service.compare_snapshot_to_current(
        saved.snapshot_id,
        UniverseScreeningFilters(sort_by="rank"),
    )
    by_ticker = {row.ticker: row for row in compared}

    assert by_ticker["ALP.PA"].snapshot_rank == 2
    assert by_ticker["ALP.PA"].current_rank == 1
    assert by_ticker["ALP.PA"].rank_change == 1
    assert by_ticker["ALP.PA"].total_score_change == pytest.approx(25.0)
    assert by_ticker["BET.PA"].snapshot_rank == 1
    assert by_ticker["BET.PA"].current_rank == 2
    assert by_ticker["BET.PA"].rank_change == -1
    assert by_ticker["BET.PA"].total_score_change == pytest.approx(-10.0)
    assert by_ticker["GAM.PA"].snapshot_rank == 3
    assert by_ticker["GAM.PA"].current_rank == 3
    assert by_ticker["GAM.PA"].rank_change == 0
    assert by_ticker["GAM.PA"].total_score_change == pytest.approx(-10.0)


# --- Phase 19: data quality and freshness filters ---


def _make_company_with_refresh(
    db_session,
    *,
    isin: str,
    ticker: str,
    name: str,
    last_universe_refresh_at=None,
) -> Company:
    company = company_repository.create(
        db_session,
        Company(
            isin=isin,
            ticker=ticker,
            name=name,
            country="France",
            sector="Tech",
            currency="EUR",
            is_active=True,
            market_cap=100_000_000.0,
            average_daily_volume=50_000.0,
        ),
    )
    if last_universe_refresh_at is not None:
        company.last_universe_refresh_at = last_universe_refresh_at
        company_repository.update(db_session, company)
    return company


def test_filter_by_min_data_quality_score_excludes_low_quality(db_session):
    alpha = _make_company_with_refresh(db_session, isin="FR0000930001", ticker="ALQ.PA", name="AlphaQ")
    beta = _make_company_with_refresh(db_session, isin="FR0000930002", ticker="BEQ.PA", name="BetaQ")

    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=alpha.id,
            snapshot_date=date(2025, 1, 1),
            metrics={"total_score": 85.0, "data_quality_score": 0.9},
            source="test",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=beta.id,
            snapshot_date=date(2025, 1, 1),
            metrics={"total_score": 80.0, "data_quality_score": 0.3},
            source="test",
        ),
    )

    service = _make_screening_service(db_session)
    rows = service.filter_universe_with_scores(UniverseScreeningFilters(min_data_quality_score=0.7))
    tickers = [r.ticker for r in rows]

    assert "ALQ.PA" in tickers
    assert "BEQ.PA" not in tickers


def test_filter_by_min_data_quality_score_excludes_missing_quality(db_session):
    alpha = _make_company_with_refresh(db_session, isin="FR0000940001", ticker="AMQ.PA", name="AlphaMQ")

    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=alpha.id,
            snapshot_date=date(2025, 1, 1),
            metrics={"total_score": 85.0},
            source="test",
        ),
    )

    service = _make_screening_service(db_session)
    rows = service.filter_universe_with_scores(UniverseScreeningFilters(min_data_quality_score=0.5))

    assert not any(r.ticker == "AMQ.PA" for r in rows)


def test_stale_only_filter_includes_company_with_no_refresh(db_session):
    alpha = _make_company_with_refresh(db_session, isin="FR0000950001", ticker="AST.PA", name="AlphaST")

    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=alpha.id,
            snapshot_date=date(2025, 1, 1),
            metrics={"total_score": 85.0},
            source="test",
        ),
    )

    service = _make_screening_service(db_session)
    rows = service.filter_universe_with_scores(UniverseScreeningFilters(stale_only=True))

    assert any(r.ticker == "AST.PA" for r in rows)


def test_stale_only_filter_includes_company_refreshed_long_ago(db_session):
    from datetime import timedelta

    old_refresh = datetime.now(UTC) - timedelta(days=60)
    alpha = _make_company_with_refresh(
        db_session,
        isin="FR0000960001",
        ticker="AOL.PA",
        name="AlphaOld",
        last_universe_refresh_at=old_refresh,
    )

    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=alpha.id,
            snapshot_date=date(2025, 1, 1),
            metrics={"total_score": 80.0},
            source="test",
        ),
    )

    service = _make_screening_service(db_session)
    rows = service.filter_universe_with_scores(UniverseScreeningFilters(stale_only=True))

    assert any(r.ticker == "AOL.PA" for r in rows)


def test_stale_only_filter_excludes_recently_refreshed_company(db_session):
    from datetime import timedelta

    fresh_refresh = datetime.now(UTC) - timedelta(days=5)
    alpha = _make_company_with_refresh(
        db_session,
        isin="FR0000970001",
        ticker="AFR.PA",
        name="AlphaFresh",
        last_universe_refresh_at=fresh_refresh,
    )

    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=alpha.id,
            snapshot_date=date(2025, 1, 1),
            metrics={"total_score": 80.0},
            source="test",
        ),
    )

    service = _make_screening_service(db_session)
    rows = service.filter_universe_with_scores(UniverseScreeningFilters(stale_only=True))

    assert not any(r.ticker == "AFR.PA" for r in rows)


def test_universe_screening_entry_exposes_freshness_and_quality_fields(db_session):
    from datetime import timedelta

    refresh_at = datetime.now(UTC) - timedelta(days=10)
    company = _make_company_with_refresh(
        db_session,
        isin="FR0000980001",
        ticker="AFQ.PA",
        name="AlphaFQ",
        last_universe_refresh_at=refresh_at,
    )

    snap_date = date(2025, 3, 15)
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=company.id,
            snapshot_date=snap_date,
            metrics={"total_score": 88.0, "data_quality_score": 0.85},
            source="test",
        ),
    )

    service = _make_screening_service(db_session)
    rows = service.filter_universe_with_scores(UniverseScreeningFilters())
    row = next(r for r in rows if r.ticker == "AFQ.PA")

    assert row.snapshot_date == snap_date
    assert row.data_quality_score == pytest.approx(0.85)
    assert row.last_universe_refresh_at is not None
