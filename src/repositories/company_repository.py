from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.company import Company
from src.repositories.seed_universe_repository import SeedUniverseEntry


def create(session: Session, company: Company) -> Company:
    session.add(company)
    session.flush()
    return company


def get_by_id(session: Session, company_id: int) -> Company | None:
    return session.get(Company, company_id)


def get_by_isin(session: Session, isin: str) -> Company | None:
    stmt = select(Company).where(Company.isin == isin)
    return session.execute(stmt).scalar_one_or_none()


def get_by_ticker(session: Session, ticker: str) -> Company | None:
    stmt = select(Company).where(Company.ticker == ticker)
    return session.execute(stmt).scalar_one_or_none()


def get_all(session: Session) -> list[Company]:
    stmt = select(Company).order_by(Company.name)
    return list(session.execute(stmt).scalars())


def search_by_name(session: Session, query: str) -> list[Company]:
    stmt = select(Company).where(Company.name.ilike(f"%{query}%")).order_by(Company.name)
    return list(session.execute(stmt).scalars())


def update(session: Session, company: Company) -> Company:
    session.flush()
    return company


def bulk_upsert_from_seed(session: Session, entries: list[SeedUniverseEntry]) -> list[Company]:
    upserted_by_id: dict[int, Company] = {}

    for entry in entries:
        by_isin = get_by_isin(session, entry.isin)
        by_ticker = get_by_ticker(session, entry.ticker)

        if by_isin is not None and by_ticker is not None and by_isin.id != by_ticker.id:
            session.delete(by_ticker)
            session.flush()
            target = by_isin
        else:
            target = by_isin or by_ticker

        if target is None:
            target = create(
                session,
                Company(
                    isin=entry.isin,
                    ticker=entry.ticker,
                    name=entry.name,
                    country=entry.country,
                    sector=entry.sector,
                    market=entry.exchange,
                    currency=entry.currency,
                ),
            )
        else:
            target.isin = entry.isin
            target.ticker = entry.ticker
            target.name = entry.name
            target.country = entry.country
            target.sector = entry.sector
            target.market = entry.exchange
            target.currency = entry.currency
            update(session, target)

        upserted_by_id[target.id] = target

    return list(upserted_by_id.values())


def delete(session: Session, company_id: int) -> bool:
    company = get_by_id(session, company_id)
    if company is None:
        return False
    session.delete(company)
    session.flush()
    return True
