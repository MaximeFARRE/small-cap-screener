from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models.company import Company
from src.models.dividend import Dividend
from src.models.financial_statement import FinancialStatement, PeriodType
from src.models.price_history import PriceHistory as PriceHistoryModel
from src.models.split import Split
from src.repositories import (
    company_repository,
    dividend_repository,
    financial_statement_repository,
    price_history_repository,
    split_repository,
)
from src.repositories.providers.base import (
    BaseProvider,
    DividendData,
    FinancialData,
    SplitData,
)
from src.repositories.providers.base import (
    PriceHistory as ProviderPriceHistory,
)


@dataclass
class SyncResult:
    company_id: int
    prices_added: int
    statements_added: int
    dividends_added: int = 0
    splits_added: int = 0


def _upsert_company(session: Session, provider: BaseProvider, ticker: str, isin: str) -> Company:
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


def _store_prices(session: Session, provider: BaseProvider, company: Company, period: str) -> int:
    records = provider.get_price_history(company.ticker, period)
    return _store_price_records(session, company, records)


def _store_price_records(session: Session, company: Company, records: list[ProviderPriceHistory]) -> int:
    added = 0
    for r in records:
        if price_history_repository.get_by_company_and_date(session, company.id, r.date):
            continue
        price_history_repository.create(
            session,
            PriceHistoryModel(
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


def _store_statements(session: Session, provider: BaseProvider, company: Company, years: int) -> int:
    statements = provider.get_financial_statements(company.ticker, years)
    return _store_statement_records(session, company, statements)


def _store_statement_records(session: Session, company: Company, statements: list[FinancialData]) -> int:
    added = 0
    for data in statements:
        period = PeriodType(data.period_type)
        if financial_statement_repository.get_by_company_and_year(session, company.id, data.fiscal_year, period):
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
                gross_profit=data.gross_profit,
                current_assets=data.current_assets,
                current_liabilities=data.current_liabilities,
                interest_expense=data.interest_expense,
            ),
        )
        added += 1
    return added


def _store_dividend_records(session: Session, company: Company, dividends: list[DividendData]) -> int:
    added = 0
    for data in dividends:
        existing = dividend_repository.get_by_company_and_ex_date(session, company.id, data.ex_date)
        dividend_repository.upsert(
            session,
            Dividend(
                company_id=company.id,
                ex_date=data.ex_date,
                payment_date=data.payment_date,
                amount=data.amount,
                currency=company.currency,
                dividend_type=None,
            ),
        )
        if existing is None:
            added += 1
    return added


def _store_split_records(session: Session, company: Company, splits: list[SplitData]) -> int:
    added = 0
    for data in splits:
        existing = split_repository.get_by_company_and_date(session, company.id, data.split_date)
        split_repository.upsert(
            session,
            Split(
                company_id=company.id,
                split_date=data.split_date,
                ratio_from=data.ratio_from,
                ratio_to=data.ratio_to,
            ),
        )
        if existing is None:
            added += 1
    return added


def sync_company_from_payload(
    session: Session,
    company: Company,
    price_history: list[ProviderPriceHistory],
    financial_statements: list[FinancialData],
    dividends: list[DividendData] | None = None,
    splits: list[SplitData] | None = None,
) -> SyncResult:
    prices_added = _store_price_records(session, company, price_history)
    statements_added = _store_statement_records(session, company, financial_statements)
    dividends_added = _store_dividend_records(session, company, dividends or [])
    splits_added = _store_split_records(session, company, splits or [])
    return SyncResult(
        company_id=company.id,
        prices_added=prices_added,
        statements_added=statements_added,
        dividends_added=dividends_added,
        splits_added=splits_added,
    )


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
