from __future__ import annotations

from dataclasses import dataclass

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
