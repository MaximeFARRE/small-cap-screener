from pydantic import BaseModel, ConfigDict


class ScoreWeightEntrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    weight: float


class ScoreCategoryContributionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    sub_score: float
    weight: float
    weighted_points: float


class ScoreMetricDriverSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    metric: str
    raw_value: float
    metric_score: float
    weighted_points: float
    impact_points: float


class ScoreBreakdownSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_score: float | None
    quality: float | None
    value: float | None
    growth: float | None
    risk: float | None
    weights: list[ScoreWeightEntrySchema]
    category_contributions: list[ScoreCategoryContributionSchema]
    positive_drivers: list[ScoreMetricDriverSchema]
    negative_drivers: list[ScoreMetricDriverSchema]
    strengths: list[str]
    weaknesses: list[str]
    summary: str
