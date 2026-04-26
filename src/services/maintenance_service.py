import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from src.repositories.database import DATABASE_URL, engine

_LOGGER = logging.getLogger(__name__)


class MaintenanceService:
    def __init__(self, database_url: str = DATABASE_URL) -> None:
        self._database_url = database_url
        if self._database_url.startswith("sqlite:///"):
            self._db_path = Path(self._database_url.removeprefix("sqlite:///"))
        else:
            self._db_path = None

    def is_sqlite(self) -> bool:
        return self._db_path is not None

    def get_database_path(self) -> Path | None:
        return self._db_path

    def backup_database(self, destination_dir: Path | None = None) -> Path:
        """Create a backup of the SQLite database file."""
        if not self.is_sqlite() or self._db_path is None:
            raise RuntimeError("Backup is only supported for local SQLite databases.")

        if not self._db_path.exists():
            raise FileNotFoundError(f"Database file not found at {self._db_path}")

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self._db_path.stem}_{timestamp}{self._db_path.suffix}.bak"

        target_dir = destination_dir if destination_dir is not None else self._db_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        backup_path = target_dir / backup_name

        shutil.copy2(self._db_path, backup_path)
        _LOGGER.info("Database backed up to %s", backup_path)
        return backup_path

    def vacuum_database(self) -> None:
        """Run VACUUM on the database to reclaim space and optimize."""
        if not self.is_sqlite():
            raise RuntimeError("Vacuum is only supported for local SQLite databases.")

        _LOGGER.info("Running VACUUM on database...")
        with engine.connect() as connection:
            # Must run VACUUM outside of a transaction
            connection.execution_options(isolation_level="AUTOCOMMIT").execute(text("VACUUM"))
        _LOGGER.info("VACUUM completed successfully.")

    def reset_demo_data(self) -> None:
        """Clear all user data from the database."""
        _LOGGER.warning("Resetting all database data...")
        with engine.begin() as connection:
            tables = [
                "screening_snapshots",
                "watchlist_entries",
                "kpi_snapshots",
                "financial_statements",
                "dividends",
                "splits",
                "price_history",
                "companies",
            ]
            # SQLite does not have TRUNCATE, so we use DELETE
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            for table in tables:
                connection.exec_driver_sql(f"DELETE FROM {table}")
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        _LOGGER.info("All data reset successfully.")
