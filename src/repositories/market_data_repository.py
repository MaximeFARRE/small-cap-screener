from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models.company import Company
from src.models.financial_statement import FinancialStatement, PeriodType
from src.models.price_history import PriceHistory
from src.repositories import (
    company_repository,
    financial_statement_repository,
    price_history_repository,
)
from src.repositories.providers.base import BaseProvider


@dataclass
class SyncResult:
    company_id: int
    prices_added: int
    statements_added: int


def _upsert_company(
    session: Session, provider: BaseProvider, ticker: str, isin: str
) -> Company:
    info = provider.get_company_info(ticker)
    existing = company_repository.get_by_isin(session, isin)
    if existing is not None:
        existing.name = info.name
        existing.sector = info.sector
        existing.market = info.market
        existing.currency = info.currency
        return company_repository.update(session, existing)
    return company_repository.create(
        session,
        Company(
            isin=isin,
            ticker=ticker,
            name=info.name,
            sector=info.sector,
            market=info.market,
            currency=info.currency,
        ),
    )


def _store_prices(
    session: Session, provider: BaseProvider, company: Company, period: str
) -> int:
    records = provider.get_price_history(company.ticker, period)
    added = 0
    for r in records:
        if price_history_repository.get_by_company_and_date(
            session, company.id, r.date
        ):
            continue
        price_history_repository.create(
            session,
            PriceHistory(
                company_id=company.id,
                date=r.date,
                open=r.open,
                high=r.high,
                low=r.low,
                close=r.close,
                adjusted_close=r.adjusted_close,
                volume=r.volume,
            ),
        )
        added += 1
    return added


def _store_statements(
    session: Session, provider: BaseProvider, company: Company, years: int
) -> int:
    statements = provider.get_financial_statements(company.ticker, years)
    added = 0
    for data in statements:
        period = PeriodType(data.period_type)
        if financial_statement_repository.get_by_company_and_year(
            session, company.id, data.fiscal_year, period
        ):
            continue
        financial_statement_repository.create(
            session,
            FinancialStatement(
                company_id=company.id,
                fiscal_year=data.fiscal_year,
                period_type=data.period_type,
                revenue=data.revenue,
                ebit=data.ebit,
                ebitda=data.ebitda,
                net_income=data.net_income,
                total_assets=data.total_assets,
                total_equity=data.total_equity,
                total_debt=data.total_debt,
                net_debt=data.net_debt,
                free_cash_flow=data.free_cash_flow,
                shares_outstanding=data.shares_outstanding,
            ),
        )
        added += 1
    return added


def sync_company(
    session: Session,
    provider: BaseProvider,
    ticker: str,
    isin: str,
    period: str = "5y",
    years: int = 5,
) -> SyncResult:
    company = _upsert_company(session, provider, ticker, isin)
    prices_added = _store_prices(session, provider, company, period)
    statements_added = _store_statements(session, provider, company, years)
    return SyncResult(
        company_id=company.id,
        prices_added=prices_added,
        statements_added=statements_added,
    )
