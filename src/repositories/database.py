import os
import pathlib
from collections.abc import Generator
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/screener.db")

_connect_args: dict = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    if DATABASE_URL.startswith("sqlite"):
        db_path = DATABASE_URL.removeprefix("sqlite:///")
        pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    import src.models.company  # noqa: F401
    import src.models.company_executive  # noqa: F401
    import src.models.company_holder  # noqa: F401
    import src.models.company_insider_transaction  # noqa: F401
    import src.models.dividend  # noqa: F401
    import src.models.financial_statement  # noqa: F401
    import src.models.kpi_snapshot  # noqa: F401
    import src.models.price_history  # noqa: F401
    import src.models.screening_snapshot  # noqa: F401
    import src.models.split  # noqa: F401
    import src.models.watchlist_entry  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_company_columns()
    _ensure_company_isin_nullable()
    _ensure_watchlist_memo_columns()
    _ensure_company_enrichment_columns()
    _ensure_company_profile_columns()
    _ensure_company_fundamental_columns()
    _ensure_financial_statement_columns()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _ensure_watchlist_memo_columns() -> None:
    memo_columns: dict[str, str] = {
        "investment_thesis": "VARCHAR(2000)",
        "key_risks": "VARCHAR(2000)",
        "catalysts": "VARCHAR(2000)",
        "valuation_notes": "VARCHAR(2000)",
        "next_action": "VARCHAR(500)",
        "next_review_at": "DATETIME",
    }
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "watchlist_entries" not in inspector.get_table_names():
            return
        existing_columns = {column["name"] for column in inspector.get_columns("watchlist_entries")}
        for column_name, column_sql_type in memo_columns.items():
            if column_name in existing_columns:
                continue
            connection.exec_driver_sql(f"ALTER TABLE watchlist_entries ADD COLUMN {column_name} {column_sql_type}")


def _ensure_company_columns() -> None:
    company_columns: dict[str, str] = {
        "source_origin": "VARCHAR(20)",
        "last_universe_refresh_at": "DATETIME",
    }
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "companies" not in inspector.get_table_names():
            return
        existing_columns = {column["name"] for column in inspector.get_columns("companies")}
        for column_name, column_sql_type in company_columns.items():
            if column_name in existing_columns:
                continue
            connection.exec_driver_sql(f"ALTER TABLE companies ADD COLUMN {column_name} {column_sql_type}")


def _ensure_company_enrichment_columns() -> None:
    company_columns: dict[str, str] = {
        "industry": "VARCHAR(200)",
        "website": "VARCHAR(500)",
        "business_summary": "VARCHAR(4000)",
        "beta": "FLOAT",
        "analyst_target_price": "FLOAT",
        "analyst_recommendation": "VARCHAR(20)",
        "analyst_count": "INTEGER",
        "forward_pe": "FLOAT",
        "enterprise_value_yahoo": "FLOAT",
    }
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "companies" not in inspector.get_table_names():
            return
        existing_columns = {column["name"] for column in inspector.get_columns("companies")}
        for column_name, column_sql_type in company_columns.items():
            if column_name in existing_columns:
                continue
            connection.exec_driver_sql(f"ALTER TABLE companies ADD COLUMN {column_name} {column_sql_type}")


def _ensure_company_profile_columns() -> None:
    profile_columns: dict[str, str] = {
        "full_time_employees": "INTEGER",
        "city": "VARCHAR(100)",
        "phone": "VARCHAR(50)",
    }
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "companies" not in inspector.get_table_names():
            return
        existing_columns = {column["name"] for column in inspector.get_columns("companies")}
        for column_name, column_sql_type in profile_columns.items():
            if column_name in existing_columns:
                continue
            connection.exec_driver_sql(f"ALTER TABLE companies ADD COLUMN {column_name} {column_sql_type}")


def _ensure_company_fundamental_columns() -> None:
    columns: dict[str, str] = {
        "gross_margins": "FLOAT",
        "operating_margins": "FLOAT",
        "profit_margins": "FLOAT",
        "roe": "FLOAT",
        "roa": "FLOAT",
        "current_ratio": "FLOAT",
        "quick_ratio": "FLOAT",
        "payout_ratio": "FLOAT",
        "shares_outstanding": "FLOAT",
        "float_shares": "FLOAT",
        "dividend_rate": "FLOAT",
        "dividend_yield": "FLOAT",
        "ex_dividend_date": "DATETIME",
        "five_year_avg_dividend_yield": "FLOAT",
    }
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "companies" not in inspector.get_table_names():
            return
        existing_columns = {column["name"] for column in inspector.get_columns("companies")}
        for column_name, column_sql_type in columns.items():
            if column_name in existing_columns:
                continue
            connection.exec_driver_sql(f"ALTER TABLE companies ADD COLUMN {column_name} {column_sql_type}")


def _ensure_financial_statement_columns() -> None:
    stmt_columns: dict[str, str] = {
        "gross_profit": "FLOAT",
        "current_assets": "FLOAT",
        "current_liabilities": "FLOAT",
        "interest_expense": "FLOAT",
    }
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "financial_statements" not in inspector.get_table_names():
            return
        existing_columns = {column["name"] for column in inspector.get_columns("financial_statements")}
        for column_name, column_sql_type in stmt_columns.items():
            if column_name in existing_columns:
                continue
            connection.exec_driver_sql(f"ALTER TABLE financial_statements ADD COLUMN {column_name} {column_sql_type}")


def _ensure_company_isin_nullable() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "companies" not in inspector.get_table_names():
            return
        columns = {column["name"]: column for column in inspector.get_columns("companies")}
        isin_column = columns.get("isin")
        if isin_column is None:
            return
        if isin_column.get("nullable", True):
            return
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.exec_driver_sql(
            """
            CREATE TABLE companies_migrated (
                id INTEGER NOT NULL PRIMARY KEY,
                isin VARCHAR(12),
                ticker VARCHAR(20),
                name VARCHAR(200) NOT NULL,
                country VARCHAR(100),
                sector VARCHAR(100),
                market VARCHAR(100),
                currency VARCHAR(3) NOT NULL,
                is_active BOOLEAN NOT NULL,
                market_cap FLOAT,
                average_daily_volume FLOAT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                source_origin VARCHAR(20),
                last_universe_refresh_at DATETIME
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO companies_migrated (
                id,
                isin,
                ticker,
                name,
                country,
                sector,
                market,
                currency,
                is_active,
                market_cap,
                average_daily_volume,
                created_at,
                updated_at,
                source_origin,
                last_universe_refresh_at
            )
            SELECT
                id,
                isin,
                ticker,
                name,
                country,
                sector,
                market,
                currency,
                is_active,
                market_cap,
                average_daily_volume,
                created_at,
                updated_at,
                source_origin,
                last_universe_refresh_at
            FROM companies
            """
        )
        connection.exec_driver_sql("DROP TABLE companies")
        connection.exec_driver_sql("ALTER TABLE companies_migrated RENAME TO companies")
        connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS ix_companies_isin ON companies (isin)")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_companies_ticker ON companies (ticker)")
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
