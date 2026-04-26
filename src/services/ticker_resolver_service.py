from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field

from src.repositories.providers.base import (
    BaseProvider,
    CompanyProfile,
    DataFetchError,
    ProviderDataInconsistentError,
    TickerNotFoundError,
)

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


@dataclass
class TickerResolverService:
    provider: BaseProvider
    french_suffixes: tuple[str, ...] = field(default=_FRENCH_SUFFIXES)

    def resolve(self, raw_ticker: str) -> TickerResolutionResult:
        normalized = _normalize(raw_ticker)
        _LOGGER.info("ticker resolution started | input=%s normalized=%s", raw_ticker, normalized)

        outcome = self._try_ticker(normalized)
        if outcome == "found":
            profile = self._fetch_profile(normalized)
            _LOGGER.info("ticker resolved directly | ticker=%s", normalized)
            return TickerResolutionResult(
                original_input=normalized,
                resolved_ticker=normalized,
                suffix_added=None,
                profile=profile,
                error=None,
                error_kind=None,
            )
        if outcome not in ("not_found",):
            # Hard provider error — do not attempt suffix fallback.
            error_msg, error_kind = outcome
            return TickerResolutionResult(
                original_input=normalized,
                resolved_ticker=None,
                suffix_added=None,
                profile=None,
                error=error_msg,
                error_kind=error_kind,
            )

        if _has_suffix(normalized):
            _LOGGER.warning(
                "ticker resolution failed, suffix already present | ticker=%s",
                normalized,
            )
            return TickerResolutionResult(
                original_input=normalized,
                resolved_ticker=None,
                suffix_added=None,
                profile=None,
                error=f"Ticker '{normalized}' introuvable chez le fournisseur.",
                error_kind=TickerErrorKind.NOT_FOUND,
            )

        for suffix in self.french_suffixes:
            candidate = f"{normalized}{suffix}"
            _LOGGER.info("ticker resolution trying suffix | candidate=%s suffix=%s", candidate, suffix)
            outcome = self._try_ticker(candidate)
            if outcome == "found":
                profile = self._fetch_profile(candidate)
                _LOGGER.info(
                    "ticker resolved via suffix | original=%s resolved=%s suffix=%s",
                    normalized,
                    candidate,
                    suffix,
                )
                return TickerResolutionResult(
                    original_input=normalized,
                    resolved_ticker=candidate,
                    suffix_added=suffix,
                    profile=profile,
                    error=None,
                    error_kind=None,
                )
            if outcome not in ("not_found",):
                error_msg, error_kind = outcome
                _LOGGER.warning(
                    "ticker resolution suffix attempt failed with provider error | candidate=%s error=%s",
                    candidate,
                    error_msg,
                )
                return TickerResolutionResult(
                    original_input=normalized,
                    resolved_ticker=None,
                    suffix_added=None,
                    profile=None,
                    error=error_msg,
                    error_kind=error_kind,
                )

        _LOGGER.warning(
            "ticker resolution exhausted all suffixes | input=%s tried=%s",
            normalized,
            [f"{normalized}{s}" for s in self.french_suffixes],
        )
        return TickerResolutionResult(
            original_input=normalized,
            resolved_ticker=None,
            suffix_added=None,
            profile=None,
            error=(
                f"Ticker '{normalized}' introuvable. "
                f"Suffixes testés : {', '.join(self.french_suffixes)}. "
                "Vérifiez le ticker (ex : MC.PA, ALAMY.PA)."
            ),
            error_kind=TickerErrorKind.NOT_FOUND,
        )

    def _try_ticker(self, ticker: str) -> str | tuple[str, TickerErrorKind]:
        """Probe the provider. Returns 'found', 'not_found', or (error_msg, kind)."""
        try:
            self.provider.get_company_profile(ticker)
            return "found"
        except TickerNotFoundError:
            _LOGGER.debug("ticker probe not found | ticker=%s", ticker)
            return "not_found"
        except ProviderDataInconsistentError as exc:
            return (f"Données incohérentes pour '{ticker}' : {exc}", TickerErrorKind.DATA_INCONSISTENT)
        except DataFetchError as exc:
            return (f"Erreur temporaire fournisseur pour '{ticker}' : {exc}", TickerErrorKind.PROVIDER_ERROR)
        except Exception as exc:
            return (f"Erreur fournisseur inattendue pour '{ticker}' : {exc}", TickerErrorKind.PROVIDER_ERROR)

    def _fetch_profile(self, ticker: str) -> CompanyProfile | None:
        try:
            return self.provider.get_company_profile(ticker)
        except Exception:
            return None


def _normalize(raw: str) -> str:
    return raw.strip().upper()


def _has_suffix(ticker: str) -> bool:
    return "." in ticker
