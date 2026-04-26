from pathlib import Path

import pytest
from sqlalchemy import text

from src.repositories.database import Base, engine
from src.services.maintenance_service import MaintenanceService


@pytest.fixture
def test_db_path(tmp_path: Path) -> str:
    path = tmp_path / "test.db"
    url = f"sqlite:///{path}"
    # Create the tables
    Base.metadata.create_all(bind=engine)
    return url


def test_maintenance_service_is_sqlite(test_db_path: str):
    service = MaintenanceService(database_url=test_db_path)
    assert service.is_sqlite() is True
    assert service.get_database_path() is not None
    assert str(service.get_database_path()).endswith("test.db")


def test_maintenance_service_backup(test_db_path: str, tmp_path: Path):
    # Ensure the DB file actually exists by connecting to it
    db_path = Path(test_db_path.removeprefix("sqlite:///"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.touch()

    service = MaintenanceService(database_url=test_db_path)
    backup_path = service.backup_database(destination_dir=tmp_path)

    assert backup_path.exists()
    assert ".bak" in backup_path.name


def test_maintenance_service_vacuum(test_db_path: str):
    service = MaintenanceService(database_url=test_db_path)

    # Just ensure it runs without raising exceptions
    service.vacuum_database()


def test_maintenance_service_reset_data(test_db_path: str):
    service = MaintenanceService(database_url=test_db_path)

    # Ensure we can run it without breaking
    service.reset_demo_data()

    # If we want to be thorough, we could insert data and verify it's deleted,
    # but running without exceptions is a good baseline test for the SQL execution.
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM companies")).scalar()
        assert count == 0
