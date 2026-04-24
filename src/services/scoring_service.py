from __future__ import annotations

from src.services.ratio_service import CompanyRatios

# Weights must sum to 1.0
_WEIGHTS: dict[str, float] = {
    "pe_ratio": 0.20,
    "ev_ebitda": 0.20,
    "pb_ratio": 0.10,
    "price_to_fcf": 0.10,
    "roe": 0.15,
    "net_margin": 0.10,
    "ebit_margin": 0.05,
    "net_debt_to_ebitda": 0.10,
}

# (good_threshold, bad_threshold, lower_is_better)
_THRESHOLDS: dict[str, tuple[float, float, bool]] = {
    "pe_ratio": (10.0, 25.0, True),
    "ev_ebitda": (6.0, 15.0, True),
    "pb_ratio": (1.0, 3.0, True),
    "price_to_fcf": (10.0, 25.0, True),
    "roe": (0.15, 0.0, False),
    "net_margin": (0.10, 0.0, False),
    "ebit_margin": (0.10, 0.0, False),
    "net_debt_to_ebitda": (1.0, 4.0, True),
}


def _score_metric(value: float, good: float, bad: float, lower_is_better: bool) -> float:
    if lower_is_better:
        if value <= good:
            return 1.0
        if value >= bad:
            return 0.0
        return 1.0 - (value - good) / (bad - good)
    else:
        if value >= good:
            return 1.0
        if value <= bad:
            return 0.0
        return (value - bad) / (good - bad)


def compute_score(ratios: CompanyRatios) -> float:
    total_weight = 0.0
    weighted_score = 0.0

    for metric, weight in _WEIGHTS.items():
        value: float | None = getattr(ratios, metric)
        if value is None:
            continue
        good, bad, lower_is_better = _THRESHOLDS[metric]
        score = _score_metric(value, good, bad, lower_is_better)
        weighted_score += score * weight
        total_weight += weight

    if total_weight < 1e-9:
        return 0.0
    return round((weighted_score / total_weight) * 100, 2)
