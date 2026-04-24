import os
import pathlib
from collections.abc import Generator
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/screener.db")

_connect_args: dict = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    if DATABASE_URL.startswith("sqlite"):
        db_path = DATABASE_URL.removeprefix("sqlite:///")
        pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    import src.models.company  # noqa: F401
    import src.models.financial_statement  # noqa: F401
    import src.models.price_history  # noqa: F401
    import src.models.screening_snapshot  # noqa: F401

    Base.metadata.create_all(bind=engine)


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
