from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from src.services.scoring_config import (
    DEFAULT_SNAPSHOT_SUB_SCORE_WEIGHTS,
    SnapshotSubScoreWeights,
    validate_snapshot_sub_score_weights,
)

_LOGGER = logging.getLogger(__name__)
_DEFAULT_SETTINGS_PATH = Path("data/settings.json")

_MIN_RETRY_ATTEMPTS: int = 1
_MAX_RETRY_ATTEMPTS: int = 10


@dataclass
class AppSettings:
    """Persisted application settings.

    All fields carry sensible defaults so the app starts correctly
    even when no settings file exists yet.
    """

    offline_mode: bool = False
    provider_retry_attempts: int = 3
    scoring_quality_weight: float = DEFAULT_SNAPSHOT_SUB_SCORE_WEIGHTS.quality_weight
    scoring_value_weight: float = DEFAULT_SNAPSHOT_SUB_SCORE_WEIGHTS.value_weight
    scoring_growth_weight: float = DEFAULT_SNAPSHOT_SUB_SCORE_WEIGHTS.growth_weight
    scoring_risk_weight: float = DEFAULT_SNAPSHOT_SUB_SCORE_WEIGHTS.risk_weight

    def scoring_weights(self) -> SnapshotSubScoreWeights:
        """Return a typed SnapshotSubScoreWeights from the current weight fields."""
        return SnapshotSubScoreWeights(
            quality_weight=self.scoring_quality_weight,
            value_weight=self.scoring_value_weight,
            growth_weight=self.scoring_growth_weight,
            risk_weight=self.scoring_risk_weight,
        )


def validate_app_settings(settings: AppSettings) -> list[str]:
    """Return a list of validation error messages. Empty list means valid."""
    errors: list[str] = []
    if not (_MIN_RETRY_ATTEMPTS <= settings.provider_retry_attempts <= _MAX_RETRY_ATTEMPTS):
        errors.append(
            f"provider_retry_attempts doit être compris entre {_MIN_RETRY_ATTEMPTS} "
            f"et {_MAX_RETRY_ATTEMPTS}, valeur reçue : {settings.provider_retry_attempts}"
        )
    try:
        validate_snapshot_sub_score_weights(settings.scoring_weights())
    except ValueError as exc:
        errors.append(str(exc))
    return errors


class SettingsService:
    """Loads and persists application settings as a JSON file on disk."""

    def __init__(self, settings_path: Path = _DEFAULT_SETTINGS_PATH) -> None:
        self._path = settings_path

    def load(self) -> AppSettings:
        """Load settings from disk. Returns defaults if file is missing or corrupt."""
        if not self._path.exists():
            _LOGGER.info("settings file not found, using defaults | path=%s", self._path)
            return AppSettings()
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _LOGGER.warning(
                "settings file unreadable, using defaults | path=%s error=%s",
                self._path,
                exc,
            )
            return AppSettings()
        return _parse_settings(raw)

    def save(self, settings: AppSettings) -> None:
        """Persist settings to disk. Creates parent directories if needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(asdict(settings), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _LOGGER.info("settings saved | path=%s", self._path)

    def reset_to_defaults(self) -> AppSettings:
        """Reset settings to factory defaults and persist them."""
        defaults = AppSettings()
        self.save(defaults)
        _LOGGER.info("settings reset to defaults | path=%s", self._path)
        return defaults


def _parse_settings(raw: object) -> AppSettings:
    """Parse a raw dict into AppSettings, ignoring unknown keys and invalid values."""
    if not isinstance(raw, dict):
        return AppSettings()
    defaults = AppSettings()
    return AppSettings(
        offline_mode=bool(raw.get("offline_mode", defaults.offline_mode)),
        provider_retry_attempts=_parse_int(
            raw.get("provider_retry_attempts"),
            defaults.provider_retry_attempts,
            _MIN_RETRY_ATTEMPTS,
            _MAX_RETRY_ATTEMPTS,
        ),
        scoring_quality_weight=_parse_float_non_negative(
            raw.get("scoring_quality_weight"),
            defaults.scoring_quality_weight,
        ),
        scoring_value_weight=_parse_float_non_negative(
            raw.get("scoring_value_weight"),
            defaults.scoring_value_weight,
        ),
        scoring_growth_weight=_parse_float_non_negative(
            raw.get("scoring_growth_weight"),
            defaults.scoring_growth_weight,
        ),
        scoring_risk_weight=_parse_float_non_negative(
            raw.get("scoring_risk_weight"),
            defaults.scoring_risk_weight,
        ),
    )


def _parse_int(value: object, default: int, min_val: int, max_val: int) -> int:
    try:
        result = int(value)  # type: ignore[arg-type]
        return result if min_val <= result <= max_val else default
    except (TypeError, ValueError):
        return default


def _parse_float_non_negative(value: object, default: float) -> float:
    try:
        result = float(value)  # type: ignore[arg-type]
        return result if result >= 0.0 else default
    except (TypeError, ValueError):
        return default
