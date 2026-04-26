from __future__ import annotations

import math
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import median

from sqlalchemy.orm import Session

from src.models.kpi_snapshot import KpiSnapshot
from src.models.price_history import PriceHistory
from src.repositories import kpi_snapshot_repository, price_history_repository
from src.repositories.database import get_session
from src.services.scoring_service import ScoringService

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]
_DEFAULT_FORWARD_DAYS = 90
_DEFAULT_MAX_SNAPSHOTS = 24
_TOP_BUCKET = "top_20"
_MIDDLE_BUCKET = "middle_60"
_BOTTOM_BUCKET = "bottom_20"
_BENCHMARK_NAME = "universe_equal_weight_proxy"


@dataclass(frozen=True)
class BucketForwardStats:
    bucket: str
    company_count: int
    valid_returns: int
    average_return: float | None
    median_return: float | None


@dataclass(frozen=True)
class SnapshotBacktestResult:
    snapshot_date: date
    company_count: int
    scored_company_count: int
    valid_forward_returns: int
    benchmark_return: float | None
    top_bucket: BucketForwardStats
    middle_bucket: BucketForwardStats
    bottom_bucket: BucketForwardStats
    top_minus_bottom: float | None


@dataclass(frozen=True)
class BacktestBucketSummary:
    bucket: str
    total_companies: int
    valid_returns: int
    average_return: float | None
    median_return: float | None
    average_excess_vs_benchmark: float | None


@dataclass(frozen=True)
class BacktestAnalysisResult:
    benchmark_name: str
    forward_days: int
    total_snapshots: int
    evaluated_snapshots: int
    snapshot_results: list[SnapshotBacktestResult]
    bucket_summaries: list[BacktestBucketSummary]
    ranking_usefulness: float | None
    hit_rate: float | None
    top_excess_vs_benchmark: float | None
    score_validation: str


@dataclass(frozen=True)
class _RankedSnapshotCompany:
    company_id: int
    total_score: float
    rank: int


@dataclass
class BacktestingService:
    session_scope_factory: SessionScopeFactory = field(default=get_session)
    scoring_service: ScoringService = field(default_factory=ScoringService)
    default_forward_days: int = _DEFAULT_FORWARD_DAYS
    default_max_snapshots: int = _DEFAULT_MAX_SNAPSHOTS

    def analyze_ranking_validation(
        self,
        *,
        forward_days: int | None = None,
        max_snapshots: int | None = None,
    ) -> BacktestAnalysisResult:
        target_forward_days = self.default_forward_days if forward_days is None else max(1, forward_days)
        target_max_snapshots = self.default_max_snapshots if max_snapshots is None else max_snapshots
        with self.session_scope_factory() as session:
            snapshot_dates = kpi_snapshot_repository.list_snapshot_dates(session)
            if target_max_snapshots > 0:
                snapshot_dates = snapshot_dates[-target_max_snapshots:]
            snapshots_by_date = {
                snapshot_date: kpi_snapshot_repository.list_by_snapshot_date(session, snapshot_date)
                for snapshot_date in snapshot_dates
            }
            company_ids = sorted(
                {snapshot.company_id for snapshots in snapshots_by_date.values() for snapshot in snapshots}
            )
            prices_by_company = {
                company_id: price_history_repository.get_by_company(session, company_id) for company_id in company_ids
            }

        snapshot_results: list[SnapshotBacktestResult] = []
        all_bucket_returns: dict[str, list[float]] = {
            _TOP_BUCKET: [],
            _MIDDLE_BUCKET: [],
            _BOTTOM_BUCKET: [],
        }
        all_bucket_excess_vs_benchmark: dict[str, list[float]] = {
            _TOP_BUCKET: [],
            _MIDDLE_BUCKET: [],
            _BOTTOM_BUCKET: [],
        }
        top_minus_bottom_values: list[float] = []
        hit_count = 0
        top_excess_values: list[float] = []

        for snapshot_date in snapshot_dates:
            snapshots = snapshots_by_date.get(snapshot_date, [])
            ranked = _rank_snapshots(snapshots, self.scoring_service)
            bucket_assignments = _assign_buckets(ranked)
            forward_returns = {
                company.company_id: _compute_forward_return(
                    prices_by_company.get(company.company_id, []),
                    snapshot_date=snapshot_date,
                    forward_days=target_forward_days,
                )
                for company in ranked
            }
            valid_returns = [value for value in forward_returns.values() if value is not None]
            benchmark_return = _average(valid_returns)
            bucket_stats = {
                bucket: _build_bucket_stats(bucket, bucket_assignments[bucket], forward_returns)
                for bucket in (_TOP_BUCKET, _MIDDLE_BUCKET, _BOTTOM_BUCKET)
            }
            top_minus_bottom = _difference(
                bucket_stats[_TOP_BUCKET].average_return,
                bucket_stats[_BOTTOM_BUCKET].average_return,
            )
            if top_minus_bottom is not None:
                top_minus_bottom_values.append(top_minus_bottom)
                if top_minus_bottom > 0:
                    hit_count += 1

            if benchmark_return is not None and bucket_stats[_TOP_BUCKET].average_return is not None:
                top_excess_values.append(bucket_stats[_TOP_BUCKET].average_return - benchmark_return)

            for bucket_name in bucket_stats:
                bucket_returns = [
                    value
                    for company in bucket_assignments[bucket_name]
                    for value in [forward_returns.get(company.company_id)]
                    if value is not None
                ]
                all_bucket_returns[bucket_name].extend(bucket_returns)
                if benchmark_return is not None:
                    all_bucket_excess_vs_benchmark[bucket_name].extend(
                        [value - benchmark_return for value in bucket_returns]
                    )

            snapshot_results.append(
                SnapshotBacktestResult(
                    snapshot_date=snapshot_date,
                    company_count=len(snapshots),
                    scored_company_count=len(ranked),
                    valid_forward_returns=len(valid_returns),
                    benchmark_return=benchmark_return,
                    top_bucket=bucket_stats[_TOP_BUCKET],
                    middle_bucket=bucket_stats[_MIDDLE_BUCKET],
                    bottom_bucket=bucket_stats[_BOTTOM_BUCKET],
                    top_minus_bottom=top_minus_bottom,
                )
            )

        bucket_summaries = [
            _build_bucket_summary(
                bucket_name,
                returns=all_bucket_returns[bucket_name],
                excess_returns=all_bucket_excess_vs_benchmark[bucket_name],
            )
            for bucket_name in (_TOP_BUCKET, _MIDDLE_BUCKET, _BOTTOM_BUCKET)
        ]
        evaluated_snapshots = len(top_minus_bottom_values)
        ranking_usefulness = _average(top_minus_bottom_values)
        hit_rate = (hit_count / evaluated_snapshots) if evaluated_snapshots > 0 else None
        top_excess_vs_benchmark = _average(top_excess_values)
        return BacktestAnalysisResult(
            benchmark_name=_BENCHMARK_NAME,
            forward_days=target_forward_days,
            total_snapshots=len(snapshot_dates),
            evaluated_snapshots=evaluated_snapshots,
            snapshot_results=snapshot_results,
            bucket_summaries=bucket_summaries,
            ranking_usefulness=ranking_usefulness,
            hit_rate=hit_rate,
            top_excess_vs_benchmark=top_excess_vs_benchmark,
            score_validation=_score_validation_label(ranking_usefulness, hit_rate),
        )


def _rank_snapshots(snapshots: list[KpiSnapshot], scoring_service: ScoringService) -> list[_RankedSnapshotCompany]:
    scored_companies: list[tuple[int, float]] = []
    for snapshot in snapshots:
        score = _snapshot_total_score(snapshot, scoring_service)
        if score is None:
            continue
        scored_companies.append((snapshot.company_id, score))
    scored_companies.sort(key=lambda item: (-item[1], item[0]))
    return [
        _RankedSnapshotCompany(company_id=company_id, total_score=score, rank=index)
        for index, (company_id, score) in enumerate(scored_companies, start=1)
    ]


def _snapshot_total_score(snapshot: KpiSnapshot, scoring_service: ScoringService) -> float | None:
    direct_score = _as_finite_float(snapshot.metrics.get("total_score"))
    if direct_score is not None:
        return direct_score
    computed = scoring_service.compute_metrics_scores(snapshot.metrics)
    return _as_finite_float(computed.total)


def _assign_buckets(ranked: list[_RankedSnapshotCompany]) -> dict[str, list[_RankedSnapshotCompany]]:
    count = len(ranked)
    if count == 0:
        return {_TOP_BUCKET: [], _MIDDLE_BUCKET: [], _BOTTOM_BUCKET: []}

    top_size = max(1, math.ceil(count * 0.2))
    bottom_size = max(1, math.ceil(count * 0.2))
    if top_size + bottom_size > count:
        bottom_size = max(0, count - top_size)

    top = ranked[:top_size]
    bottom = ranked[count - bottom_size :] if bottom_size > 0 else []
    middle_start = top_size
    middle_end = count - bottom_size
    middle = ranked[middle_start:middle_end]
    return {_TOP_BUCKET: top, _MIDDLE_BUCKET: middle, _BOTTOM_BUCKET: bottom}


def _compute_forward_return(
    prices_desc: list[PriceHistory],
    *,
    snapshot_date: date,
    forward_days: int,
) -> float | None:
    if not prices_desc:
        return None
    prices_asc = sorted(prices_desc, key=lambda item: item.date)
    entry_price = _first_price_on_or_after(prices_asc, snapshot_date)
    if entry_price is None or entry_price.close <= 0:
        return None
    target_date = snapshot_date + timedelta(days=forward_days)
    exit_price = _first_price_on_or_after(prices_asc, target_date)
    if exit_price is None:
        return None
    return (exit_price.close - entry_price.close) / entry_price.close


def _first_price_on_or_after(prices_asc: list[PriceHistory], target_date: date) -> PriceHistory | None:
    for item in prices_asc:
        if item.date >= target_date:
            return item
    return None


def _build_bucket_stats(
    bucket_name: str,
    members: list[_RankedSnapshotCompany],
    forward_returns: dict[int, float | None],
) -> BucketForwardStats:
    returns = [forward_returns.get(member.company_id) for member in members]
    valid = [value for value in returns if value is not None]
    return BucketForwardStats(
        bucket=bucket_name,
        company_count=len(members),
        valid_returns=len(valid),
        average_return=_average(valid),
        median_return=_median(valid),
    )


def _build_bucket_summary(
    bucket_name: str,
    *,
    returns: list[float],
    excess_returns: list[float],
) -> BacktestBucketSummary:
    return BacktestBucketSummary(
        bucket=bucket_name,
        total_companies=len(returns),
        valid_returns=len(returns),
        average_return=_average(returns),
        median_return=_median(returns),
        average_excess_vs_benchmark=_average(excess_returns),
    )


def _as_finite_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(median(values))


def _difference(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def _score_validation_label(ranking_usefulness: float | None, hit_rate: float | None) -> str:
    if ranking_usefulness is None or hit_rate is None:
        return "insufficient_data"
    if ranking_usefulness > 0.0 and hit_rate >= 0.60:
        return "validated"
    if ranking_usefulness > 0.0:
        return "mixed"
    return "not_validated"
