from __future__ import annotations

from pathlib import Path

import src.repositories.database as database


def test_resolve_database_url_uses_environment_variable(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///C:/tmp/custom.db")
    assert database._resolve_database_url() == "sqlite:///C:/tmp/custom.db"


def test_default_sqlite_path_uses_project_data_folder(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(database.sys, "frozen", False, raising=False)

    default_path = database._default_sqlite_database_path()

    assert default_path.is_absolute()
    assert default_path.name == "screener.db"
    assert default_path.parent.name == "data"


def test_default_sqlite_path_uses_executable_dir_when_frozen(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(database.sys, "frozen", True, raising=False)
    monkeypatch.setattr(database.sys, "executable", "C:/apps/screener/small-cap-screener.exe")

    default_path = database._default_sqlite_database_path()

    assert default_path == Path("C:/apps/screener/data/screener.db")
