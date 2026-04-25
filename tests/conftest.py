import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.models.company  # noqa: F401
import src.models.dividend  # noqa: F401
import src.models.financial_statement  # noqa: F401
import src.models.kpi_snapshot  # noqa: F401
import src.models.price_history  # noqa: F401
import src.models.screening_snapshot  # noqa: F401
import src.models.split  # noqa: F401
from src.repositories.database import Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
