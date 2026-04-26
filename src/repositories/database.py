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
    import src.models.dividend  # noqa: F401
    import src.models.financial_statement  # noqa: F401
    import src.models.kpi_snapshot  # noqa: F401
    import src.models.price_history  # noqa: F401
    import src.models.screening_snapshot  # noqa: F401
    import src.models.split  # noqa: F401
    import src.models.watchlist_entry  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_watchlist_memo_columns()


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
