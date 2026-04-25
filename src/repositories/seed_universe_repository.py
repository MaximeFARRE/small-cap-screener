from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS: tuple[str, ...] = (
    "name",
    "ticker",
    "isin",
    "exchange",
    "country",
    "sector",
    "currency",
)


class SeedUniverseError(Exception):
    """Base class for seed universe CSV loading errors."""


class SeedUniverseFileNotFoundError(SeedUniverseError):
    """Raised when the seed CSV file cannot be found."""


class MissingSeedColumnsError(SeedUniverseError):
    """Raised when mandatory seed columns are not present."""


class EmptySeedFileError(SeedUniverseError):
    """Raised when the seed CSV file has no content rows."""


class InvalidSeedRowError(SeedUniverseError):
    """Raised when one CSV row cannot be mapped to a valid seed entry."""


@dataclass(frozen=True)
class SeedUniverseEntry:
    name: str
    ticker: str
    isin: str
    exchange: str
    country: str
    sector: str
    currency: str


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={col: str(col).strip().lower() for col in df.columns})


def _load_csv(csv_path: Path) -> pd.DataFrame:
    try:
        dataframe = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except pd.errors.EmptyDataError as exc:
        raise EmptySeedFileError(f"Seed CSV '{csv_path}' is empty") from exc
    except Exception as exc:
        raise SeedUniverseError(f"Unable to read seed CSV '{csv_path}': {exc}") from exc

    if dataframe.empty:
        raise EmptySeedFileError(f"Seed CSV '{csv_path}' has no rows")
    return _normalize_columns(dataframe)


def _validate_required_columns(df: pd.DataFrame) -> None:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise MissingSeedColumnsError(f"Missing required column(s): {missing}")
