from __future__ import annotations

from dataclasses import dataclass

_WEIGHT_SUM_TARGET = 1.0
_WEIGHT_TOLERANCE = 1e-9


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
