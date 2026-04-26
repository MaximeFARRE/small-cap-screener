from __future__ import annotations

import logging
import re
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from src.models.company import Company
from src.repositories import company_repository
from src.repositories.database import get_session
from src.repositories.providers.base import TickerNotFoundError
from src.services.financial_data_service import FinancialDataService
from src.services.kpi_snapshot_service import KpiSnapshotService

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]
_LOGGER = logging.getLogger(__name__)

_TICKER_PATTERN = re.compile(r"^[A-Z0-9]{1,10}(\.[A-Z]{1,5})?$")
_MAX_TICKER_LENGTH = 20


@dataclass
class TickerIngestionResult:
    ticker: str
    success: bool
    company_id: int | None = None
    created: bool = False
    kpi_snapshot_id: int | None = None
    error: str | None = None
    stage: str | None = None
    warnings: list[str] = field(default_factory=list)


def validate_ticker_format(ticker: str) -> str | None:
    """Return an error message if the ticker is invalid, else None."""
    if not ticker:
        return "Le ticker ne peut pas être vide."
    if len(ticker) > _MAX_TICKER_LENGTH:
        return f"Le ticker ne peut pas dépasser {_MAX_TICKER_LENGTH} caractères."
    if not _TICKER_PATTERN.match(ticker):
        return "Format de ticker invalide. " "Exemples valides : MC.PA, ALAMY.PA, BNP, GOOGL"
    return None


def _synthetic_isin(ticker: str) -> str:
    """Generate a unique synthetic ISIN for tickers without a real one."""
    cleaned = re.sub(r"[^A-Z0-9]", "", ticker.upper())[:10]
    return f"YF{cleaned}"


@dataclass
class TickerIngestionService:
    financial_data_service: FinancialDataService
    kpi_snapshot_service: KpiSnapshotService
    session_scope_factory: SessionScopeFactory = field(default=get_session)

    def ingest_ticker(self, ticker: str) -> TickerIngestionResult:
        normalized = ticker.strip().upper()

        format_error = validate_ticker_format(normalized)
        if format_error:
            return TickerIngestionResult(
                ticker=normalized,
                success=False,
                error=format_error,
                stage="validate",
            )

        try:
            profile = self.financial_data_service.provider.get_company_profile(normalized)
        except TickerNotFoundError:
            return TickerIngestionResult(
                ticker=normalized,
                success=False,
                error=f"Ticker '{normalized}' introuvable chez le fournisseur de données.",
                stage="fetch",
            )
        except Exception as exc:
            return TickerIngestionResult(
                ticker=normalized,
                success=False,
                error=f"Erreur fournisseur : {exc}",
                stage="fetch",
            )

        company_id, created = self._find_or_create_company(normalized, profile)

        refresh_result = self.financial_data_service.refresh_company_data(company_id)
        if not refresh_result.success:
            return TickerIngestionResult(
                ticker=normalized,
                success=False,
                company_id=company_id,
                created=created,
                error=refresh_result.error,
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
                "ticker ingestion kpi failed | ticker=%s company_id=%s error=%s",
                normalized,
                company_id,
                kpi_result.error,
            )
            return TickerIngestionResult(
                ticker=normalized,
                success=True,
                company_id=company_id,
                created=created,
                warnings=warnings,
            )

        _LOGGER.info(
            "ticker ingestion succeeded | ticker=%s company_id=%s created=%s snapshot_id=%s",
            normalized,
            company_id,
            created,
            kpi_result.snapshot_id,
        )
        return TickerIngestionResult(
            ticker=normalized,
            success=True,
            company_id=company_id,
            created=created,
            kpi_snapshot_id=kpi_result.snapshot_id,
            warnings=warnings,
        )

    def _find_or_create_company(
        self,
        ticker: str,
        profile,
    ) -> tuple[int, bool]:
        with self.session_scope_factory() as session:
            existing = company_repository.get_by_ticker(session, ticker)
            if existing is not None:
                _LOGGER.info(
                    "ticker ingestion found existing company | ticker=%s company_id=%s",
                    ticker,
                    existing.id,
                )
                return existing.id, False

            isin = (profile.isin or "").strip() or _synthetic_isin(ticker)
            existing_by_isin = company_repository.get_by_isin(session, isin)
            if existing_by_isin is not None:
                _LOGGER.info(
                    "ticker ingestion found company by isin | ticker=%s isin=%s company_id=%s",
                    ticker,
                    isin,
                    existing_by_isin.id,
                )
                return existing_by_isin.id, False

            company = Company(
                isin=isin,
                ticker=ticker,
                name=profile.name,
                country=profile.country,
                sector=profile.sector,
                market=profile.market,
                currency=profile.currency or "EUR",
                is_active=True,
            )
            created_company = company_repository.create(session, company)
            _LOGGER.info(
                "ticker ingestion created new company | ticker=%s isin=%s company_id=%s",
                ticker,
                isin,
                created_company.id,
            )
            return created_company.id, True
