from __future__ import annotations

import pytest

from src.repositories.seed_universe_repository import (
    EmptySeedFileError,
    InvalidSeedRowError,
    MissingSeedColumnsError,
    read_seed_universe,
)


def test_read_seed_universe_valid_csv(tmp_path):
    csv_path = tmp_path / "seed_universe.csv"
    csv_path.write_text(
        (
            "name,ticker,isin,exchange,country,sector,currency\n"
            "TotalEnergies,TTE.PA,FR0000120271,PAR,France,Energy,EUR\n"
            "Air Liquide,AI.PA,FR0000120073,PAR,France,Chemicals,EUR\n"
        ),
        encoding="utf-8",
    )

    entries = read_seed_universe(csv_path)

    assert len(entries) == 2
    assert entries[0].name == "TotalEnergies"
    assert entries[0].ticker == "TTE.PA"
    assert entries[1].isin == "FR0000120073"


def test_read_seed_universe_missing_required_column(tmp_path):
    csv_path = tmp_path / "seed_universe_missing.csv"
    csv_path.write_text(
        ("name,ticker,isin,exchange,country,currency\nTotalEnergies,TTE.PA,FR0000120271,PAR,France,EUR\n"),
        encoding="utf-8",
    )

    with pytest.raises(MissingSeedColumnsError, match="sector"):
        read_seed_universe(csv_path)


def test_read_seed_universe_empty_file(tmp_path):
    csv_path = tmp_path / "seed_universe_empty.csv"
    csv_path.write_text("", encoding="utf-8")

    with pytest.raises(EmptySeedFileError):
        read_seed_universe(csv_path)


def test_read_seed_universe_invalid_row(tmp_path):
    csv_path = tmp_path / "seed_universe_invalid_row.csv"
    csv_path.write_text(
        ("name,ticker,isin,exchange,country,sector,currency\nTotalEnergies,,FR0000120271,PAR,France,Energy,EUR\n"),
        encoding="utf-8",
    )

    with pytest.raises(InvalidSeedRowError, match="row 2"):
        read_seed_universe(csv_path)
