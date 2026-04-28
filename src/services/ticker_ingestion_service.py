from __future__ import annotations

import logging
import re
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from src.models.company import SOURCE_MANUAL, Company
from src.repositories import company_repository
from src.repositories.database import get_session
from src.services.financial_data_service import FinancialDataService
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.ticker_resolver_service import TickerErrorKind, TickerResolutionResult, TickerResolverService

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]
_LOGGER = logging.getLogger(__name__)

_TICKER_PATTERN = re.compile(r"^[A-Z0-9]{1,10}(\.[A-Z]{1,5})?$")
_ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")
_MAX_TICKER_LENGTH = 20
_MAX_IDENTIFIER_LENGTH = 30


@dataclass
class TickerIngestionResult:
    ticker: str
    success: bool
    resolved_ticker: str | None = None
    company_id: int | None = None
    created: bool = False
    kpi_snapshot_id: int | None = None
    error: str | None = None
    error_kind: str | None = None
    stage: str | None = None
    warnings: list[str] = field(default_factory=list)


def validate_ticker_format(ticker: str) -> str | None:
    """Return an error message if the ticker is invalid, else None."""
    if not ticker:
        return "Le ticker ne peut pas être vide."
    if len(ticker) > _MAX_TICKER_LENGTH:
        return f"Le ticker ne peut pas dépasser {_MAX_TICKER_LENGTH} caractères."
    if not _TICKER_PATTERN.match(ticker):
        return "Format de ticker invalide. Exemples valides : MC.PA, ALAMY.PA, BNP, GOOGL"
    return None


def validate_ingestion_identifier(identifier: str) -> str | None:
    if not identifier:
        return "Le ticker ou l'ISIN ne peut pas être vide."
    if len(identifier) > _MAX_IDENTIFIER_LENGTH:
        return f"Le ticker/ISIN ne peut pas dépasser {_MAX_IDENTIFIER_LENGTH} caractères."
    if _TICKER_PATTERN.match(identifier):
        return None
    if _ISIN_PATTERN.match(identifier):
        return None
    return "Format invalide. Exemples valides : MC.PA, ALAMY.PA, BNP, GOOGL ou ISIN comme FR0000120271."


def _normalize_provider_isin(isin: str | None) -> str | None:
    if isin is None:
        return None
    normalized = isin.strip().upper()
    if not normalized:
        return None
    if not _ISIN_PATTERN.match(normalized):
        return None
    return normalized


def _is_valid_isin(isin: str | None) -> bool:
    if isin is None:
        return False
    normalized = isin.strip().upper()
    return bool(_ISIN_PATTERN.match(normalized))


@dataclass
class TickerIngestionService:
    financial_data_service: FinancialDataService
    kpi_snapshot_service: KpiSnapshotService
    session_scope_factory: SessionScopeFactory = field(default=get_session)

    def __post_init__(self) -> None:
        self._resolver = TickerResolverService(provider=self.financial_data_service.provider)

    def ingest_ticker(self, ticker: str) -> TickerIngestionResult:
        return self.ingest_identifier(ticker)

    def ingest_identifier(self, identifier: str) -> TickerIngestionResult:
        normalized = identifier.strip().upper()
        format_error = validate_ingestion_identifier(normalized)
        if format_error:
            return TickerIngestionResult(
                ticker=normalized,
                success=False,
                error=format_error,
                stage="validate",
            )

        resolution = self._resolve_identifier(normalized)
        if not resolution.success or resolution.resolved_ticker is None or resolution.profile is None:
            return TickerIngestionResult(
                ticker=normalized,
                success=False,
                error=resolution.error or "échec de résolution ticker",
                error_kind=resolution.error_kind,
                stage="fetch",
            )

        resolved = resolution.resolved_ticker
        profile = resolution.profile
        company_id, created = self._find_or_create_company(resolved, profile)

        refresh_result = self.financial_data_service.refresh_company_data(company_id)
        if not refresh_result.success:
            return TickerIngestionResult(
                ticker=normalized,
                resolved_ticker=resolved,
                success=False,
                company_id=company_id,
                created=created,
                error=refresh_result.error,
                error_kind=refresh_result.error_kind,
                stage=refresh_result.stage,
                warnings=list(refresh_result.warnings),
            )

        kpi_result = self.kpi_snapshot_service.compute_and_upsert_for_company(
            company_id=company_id,
            snapshot_date=date.today(),
        )
        warnings = list(refresh_result.warnings)
        if not kpi_result.success:
            warnings.append(f"Snapshot KPI échoué : {kpi_result.error}")
            _LOGGER.warning(
                "ticker ingestion kpi failed | ticker=%s resolved=%s company_id=%s error=%s",
                normalized,
                resolved,
                company_id,
                kpi_result.error,
            )
            return TickerIngestionResult(
                ticker=normalized,
                resolved_ticker=resolved,
                success=True,
                company_id=company_id,
                created=created,
                warnings=warnings,
            )

        _LOGGER.info(
            "ticker ingestion succeeded | ticker=%s resolved=%s company_id=%s created=%s snapshot_id=%s",
            normalized,
            resolved,
            company_id,
            created,
            kpi_result.snapshot_id,
        )
        return TickerIngestionResult(
            ticker=normalized,
            resolved_ticker=resolved,
            success=True,
            company_id=company_id,
            created=created,
            kpi_snapshot_id=kpi_result.snapshot_id,
            warnings=warnings,
        )

    def _resolve_identifier(self, normalized_identifier: str) -> TickerResolutionResult:
        if _ISIN_PATTERN.match(normalized_identifier):
            return self._resolve_isin(normalized_identifier)
        return self._resolver.resolve(normalized_identifier)

    def _resolve_isin(self, normalized_isin: str) -> TickerResolutionResult:
        resolved_ticker = None
        if hasattr(self.financial_data_service.provider, "search_by_isin"):
            resolved_ticker = self.financial_data_service.provider.search_by_isin(normalized_isin)

        if resolved_ticker is None:
            return TickerResolutionResult(
                original_input=normalized_isin,
                resolved_ticker=None,
                suffix_added=None,
                profile=None,
                error=f"ISIN '{normalized_isin}' introuvable via la recherche du fournisseur.",
                error_kind=TickerErrorKind.NOT_FOUND,
            )

        # Une fois le ticker trouvé, on le résout normalement pour valider et récupérer le profile
        resolution = self._resolver.resolve(resolved_ticker)
        # On garde l'input original (ISIN) pour la clarté du résultat
        return TickerResolutionResult(
            original_input=normalized_isin,
            resolved_ticker=resolution.resolved_ticker,
            suffix_added=resolution.suffix_added,
            profile=resolution.profile,
            error=resolution.error,
            error_kind=resolution.error_kind,
        )

    def _find_or_create_company(
        self,
        ticker: str,
        profile,
    ) -> tuple[int, bool]:
        with self.session_scope_factory() as session:
            raw_isin = profile.isin
            provider_isin = _normalize_provider_isin(raw_isin)
            if raw_isin is not None and provider_isin is None:
                _LOGGER.warning(
                    "ticker ingestion ignored invalid provider isin | ticker=%s provider_isin=%s",
                    ticker,
                    raw_isin,
                )

            existing = company_repository.get_by_ticker(session, ticker)
            if existing is not None:
                if not _is_valid_isin(existing.isin):
                    existing.isin = provider_isin
                    company_repository.update(session, existing)
                    if provider_isin is None:
                        _LOGGER.warning(
                            "ticker ingestion cleared invalid existing isin | ticker=%s company_id=%s",
                            ticker,
                            existing.id,
                        )
                    else:
                        _LOGGER.info(
                            "ticker ingestion replaced invalid existing isin | ticker=%s company_id=%s isin=%s",
                            ticker,
                            existing.id,
                            provider_isin,
                        )
                _LOGGER.info(
                    "ticker ingestion found existing company | ticker=%s company_id=%s",
                    ticker,
                    existing.id,
                )
                return existing.id, False

            if provider_isin is None:
                _LOGGER.warning(
                    "ticker ingestion continues without isin | ticker=%s",
                    ticker,
                )
            else:
                existing_by_isin = company_repository.get_by_isin(session, provider_isin)
                if existing_by_isin is not None:
                    _LOGGER.info(
                        "ticker ingestion found company by isin | ticker=%s isin=%s company_id=%s",
                        ticker,
                        provider_isin,
                        existing_by_isin.id,
                    )
                    return existing_by_isin.id, False

            company = Company(
                isin=provider_isin,
                ticker=ticker,
                name=profile.name,
                country=profile.country,
                sector=profile.sector,
                market=profile.market,
                currency=profile.currency or "EUR",
                is_active=True,
                source_origin=SOURCE_MANUAL,
            )
            created_company = company_repository.create(session, company)
            _LOGGER.info(
                "ticker ingestion created new company | ticker=%s isin=%s company_id=%s",
                ticker,
                provider_isin,
                created_company.id,
            )
            return created_company.id, True
