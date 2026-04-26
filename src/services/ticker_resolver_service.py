from __future__ import annotations

import enum
import logging
from dataclasses import dataclass

from src.repositories.providers.base import CompanyProfile

_LOGGER = logging.getLogger(__name__)

_FRENCH_SUFFIXES: tuple[str, ...] = (".PA", ".AL")


class TickerErrorKind(enum.StrEnum):
    NOT_FOUND = "not_found"
    PROVIDER_ERROR = "provider_error"
    DATA_INCONSISTENT = "data_inconsistent"


@dataclass(frozen=True)
class TickerResolutionResult:
    original_input: str
    resolved_ticker: str | None
    suffix_added: str | None
    profile: CompanyProfile | None
    error: str | None
    error_kind: TickerErrorKind | None

    @property
    def success(self) -> bool:
        return self.resolved_ticker is not None and self.error is None


def _normalize(raw: str) -> str:
    return raw.strip().upper()


def _has_suffix(ticker: str) -> bool:
    return "." in ticker
