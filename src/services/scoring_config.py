from __future__ import annotations

from dataclasses import dataclass

_WEIGHT_SUM_TARGET = 1.0
_WEIGHT_TOLERANCE = 1e-6


@dataclass(frozen=True)
class SnapshotSubScoreWeights:
    quality_weight: float
    value_weight: float
    growth_weight: float
    risk_weight: float

    def as_dict(self) -> dict[str, float]:
        return {
            "quality": self.quality_weight,
            "value": self.value_weight,
            "growth": self.growth_weight,
            "risk": self.risk_weight,
        }


DEFAULT_SNAPSHOT_SUB_SCORE_WEIGHTS = SnapshotSubScoreWeights(
    quality_weight=0.35,
    value_weight=0.30,
    growth_weight=0.20,
    risk_weight=0.15,
)


def validate_snapshot_sub_score_weights(weights: SnapshotSubScoreWeights) -> None:
    values = weights.as_dict()
    total = sum(values.values())
    if abs(total - _WEIGHT_SUM_TARGET) > _WEIGHT_TOLERANCE:
        raise ValueError(f"sub-score weights must sum to {_WEIGHT_SUM_TARGET}, got {total:.6f}")
    for category, value in values.items():
        if value < 0:
            raise ValueError(f"sub-score weight must be non-negative: {category}={value}")


@dataclass(frozen=True)
class MetricDef:
    weight: float
    good: float
    bad: float
    lower_is_better: bool


@dataclass(frozen=True)
class BlocDef:
    name: str
    weight: float
    metrics: tuple[tuple[str, MetricDef], ...]


BLOC_DEFS: tuple[BlocDef, ...] = (
    BlocDef(
        "business_quality",
        0.15,
        (
            ("gross_margin", MetricDef(0.30, 0.40, 0.15, False)),
            ("roic", MetricDef(0.30, 0.15, 0.02, False)),
            ("roce", MetricDef(0.20, 0.15, 0.02, False)),
            ("asset_turnover", MetricDef(0.20, 1.0, 0.3, False)),
        ),
    ),
    BlocDef(
        "growth_trajectory",
        0.12,
        (
            # gross_profit_growth is top priority: captures margin quality of growth
            ("gross_profit_growth", MetricDef(0.35, 0.15, -0.05, False)),
            ("revenue_growth", MetricDef(0.30, 0.12, -0.05, False)),
            ("revenue_cagr_3y", MetricDef(0.25, 0.10, -0.03, False)),
            # ebitda_growth: lower weight; not duplicated in capital_allocation
            ("ebitda_growth", MetricDef(0.10, 0.15, -0.10, False)),
        ),
    ),
    BlocDef(
        "profitability",
        0.14,
        (
            ("gross_profitability", MetricDef(0.25, 0.30, 0.05, False)),
            ("roa", MetricDef(0.20, 0.08, 0.0, False)),
            ("roic", MetricDef(0.25, 0.15, 0.02, False)),
            ("ebit_margin", MetricDef(0.30, 0.12, 0.0, False)),
        ),
    ),
    BlocDef(
        "capital_allocation",
        0.10,
        (
            # ronic = ΔEBIT (or ΔEBITDA) / Δcapital_invested; primary capital efficiency signal
            ("ronic", MetricDef(0.55, 0.15, 0.0, False)),
            # capex_to_revenue: capital-light model preferred (lower is better)
            ("capex_to_revenue", MetricDef(0.25, 0.03, 0.15, True)),
            # shares_growth: dilution penalised; buybacks rewarded (lower is better)
            ("shares_growth", MetricDef(0.20, -0.01, 0.05, True)),
        ),
    ),
    BlocDef(
        "balance_sheet_strength",
        0.14,
        (
            # Sole home for accounting leverage / coverage / liquidity
            ("net_debt_to_ebitda", MetricDef(0.35, 1.0, 4.0, True)),
            ("interest_coverage", MetricDef(0.25, 6.0, 1.5, False)),
            ("current_ratio", MetricDef(0.20, 1.5, 0.8, False)),
            ("debt_to_equity", MetricDef(0.20, 0.5, 2.0, True)),
        ),
    ),
    BlocDef(
        "cash_flow_quality",
        0.12,
        (
            # accrual_ratio moved to risk_inverse (forensic layer)
            ("cfo_to_net_income", MetricDef(0.25, 1.2, 0.5, False)),
            ("cfo_to_ebit", MetricDef(0.20, 1.0, 0.4, False)),
            ("fcf_margin", MetricDef(0.25, 0.08, -0.02, False)),
            # cfo_margin: absolute CFO level; negative CFO scores 0
            ("cfo_margin", MetricDef(0.20, 0.08, -0.02, False)),
            # cfo_streak_negative: 0=none, 1=1 year, 2=2 consecutive; lower is better
            ("cfo_streak_negative", MetricDef(0.10, 0.0, 2.0, True)),
        ),
    ),
    BlocDef(
        "valuation",
        0.10,
        (
            ("ev_ebit", MetricDef(0.30, 8.0, 20.0, True)),
            ("ev_fcf", MetricDef(0.25, 12.0, 30.0, True)),
            ("ev_sales", MetricDef(0.25, 1.0, 4.0, True)),
            ("pb_ratio", MetricDef(0.20, 1.0, 3.0, True)),
        ),
    ),
    BlocDef(
        "risk_inverse",
        0.13,
        (
            # Accounting composite — no overlap with balance_sheet metrics
            ("altman_z_proxy", MetricDef(0.40, 3.0, 1.2, False)),
            # Market layer
            ("beta", MetricDef(0.30, 0.8, 1.8, True)),
            # Forensic layer — moved from cash_flow_quality
            ("accrual_ratio", MetricDef(0.30, -0.05, 0.10, True)),
        ),
    ),
)

LEGACY_QUALITY_BLOCS: tuple[str, ...] = ("business_quality", "profitability", "cash_flow_quality")
LEGACY_VALUE_BLOCS: tuple[str, ...] = ("valuation",)
LEGACY_GROWTH_BLOCS: tuple[str, ...] = ("growth_trajectory", "capital_allocation")
LEGACY_RISK_BLOCS: tuple[str, ...] = ("balance_sheet_strength", "risk_inverse")

BLOC_TO_LEGACY: dict[str, str] = {}
for _bloc_name in LEGACY_QUALITY_BLOCS:
    BLOC_TO_LEGACY[_bloc_name] = "quality"
for _bloc_name in LEGACY_VALUE_BLOCS:
    BLOC_TO_LEGACY[_bloc_name] = "value"
for _bloc_name in LEGACY_GROWTH_BLOCS:
    BLOC_TO_LEGACY[_bloc_name] = "growth"
for _bloc_name in LEGACY_RISK_BLOCS:
    BLOC_TO_LEGACY[_bloc_name] = "risk"

CAP_DISTRESSED: float = 35.0
CAP_VALUE_TRAP: float = 45.0
CAP_DANGEROUS_DEBT: float = 45.0
CAP_CHRONIC_DILUTION: float = 55.0
CAP_UNCONFIRMED_TURNAROUND: float = 65.0

CTX_ADJ_MIN: float = -12.0
CTX_ADJ_MAX: float = 6.0

COMPENSATION_FLOOR: float = 20.0
COMPENSATION_FACTOR: float = 0.4

VALUATION_BRIDLE_THRESHOLD: float = 30.0
VALUATION_BRIDLE_CAP: float = 50.0
