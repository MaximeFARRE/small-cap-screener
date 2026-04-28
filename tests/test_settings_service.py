from pathlib import Path

from src.services.settings_service import (
    AppSettings,
    SettingsService,
    validate_app_settings,
)


def test_settings_service_load_save(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    service = SettingsService(settings_path=path)

    # Missing file returns defaults
    settings = service.load()
    assert settings.offline_mode is False
    assert settings.provider_retry_attempts == 3

    # Save updates the file
    settings.offline_mode = True
    settings.provider_retry_attempts = 5
    service.save(settings)

    assert path.exists()

    # Load reads the file
    loaded = service.load()
    assert loaded.offline_mode is True
    assert loaded.provider_retry_attempts == 5
    assert loaded.scoring_quality_weight == 0.35


def test_settings_service_reset(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    service = SettingsService(settings_path=path)

    custom = AppSettings(offline_mode=True, scoring_quality_weight=0.99)
    service.save(custom)

    reset = service.reset_to_defaults()
    assert reset.offline_mode is False
    assert reset.scoring_quality_weight == 0.35

    loaded = service.load()
    assert loaded.offline_mode is False


def test_settings_service_corrupted_file(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{ corrupt json")

    service = SettingsService(settings_path=path)
    loaded = service.load()

    assert loaded.offline_mode is False


def test_settings_service_partial_file(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"offline_mode": true}')

    service = SettingsService(settings_path=path)
    loaded = service.load()

    assert loaded.offline_mode is True
    assert loaded.provider_retry_attempts == 3


def test_validate_app_settings_valid() -> None:
    settings = AppSettings()
    errors = validate_app_settings(settings)
    assert not errors


def test_validate_app_settings_invalid_retries() -> None:
    settings = AppSettings(provider_retry_attempts=0)
    errors = validate_app_settings(settings)
    assert len(errors) == 1
    assert "provider_retry_attempts" in errors[0]


def test_validate_app_settings_invalid_weights() -> None:
    settings = AppSettings(
        scoring_quality_weight=0.5,
        scoring_value_weight=0.5,
        scoring_growth_weight=0.5,
        scoring_risk_weight=0.5,
    )
    errors = validate_app_settings(settings)
    assert len(errors) == 1
    assert "sub-score weights must sum to 1.0" in errors[0]


def test_validate_app_settings_negative_weight() -> None:
    settings = AppSettings(
        scoring_quality_weight=1.1,
        scoring_value_weight=-0.1,
        scoring_growth_weight=0.0,
        scoring_risk_weight=0.0,
    )
    errors = validate_app_settings(settings)
    assert len(errors) == 1
    assert "non-negative" in errors[0]
