from __future__ import annotations

from dataclasses import dataclass, field

from src.services.ratio_service import CompanyRatios
from src.services.scoring_service import compute_score


@dataclass
class ScreeningCriteria:
    max_pe: float | None = None
    max_pb: float | None = None
    max_ev_ebitda: float | None = None
    min_roe: float | None = None
    min_net_margin: float | None = None
    max_debt_to_equity: float | None = None
    max_net_debt_to_ebitda: float | None = None
    min_ebit_margin: float | None = None


@dataclass
class ScreeningResult:
    ratios: CompanyRatios
    score: float


def _passes(ratios: CompanyRatios, criteria: ScreeningCriteria) -> bool:
    checks: list[tuple[float | None, float | None, bool]] = [
        (ratios.pe_ratio, criteria.max_pe, True),
        (ratios.pb_ratio, criteria.max_pb, True),
        (ratios.ev_ebitda, criteria.max_ev_ebitda, True),
        (ratios.roe, criteria.min_roe, False),
        (ratios.net_margin, criteria.min_net_margin, False),
        (ratios.debt_to_equity, criteria.max_debt_to_equity, True),
        (ratios.net_debt_to_ebitda, criteria.max_net_debt_to_ebitda, True),
        (ratios.ebit_margin, criteria.min_ebit_margin, False),
    ]
    for value, threshold, is_max in checks:
        if threshold is None or value is None:
            continue
        if is_max and value > threshold:
            return False
        if not is_max and value < threshold:
            return False
    return True


def apply_filters(
    candidates: list[CompanyRatios],
    criteria: ScreeningCriteria,
) -> list[ScreeningResult]:
    results = [
        ScreeningResult(ratios=r, score=compute_score(r))
        for r in candidates
        if _passes(r, criteria)
    ]
    return sorted(results, key=lambda x: x.score, reverse=True)
