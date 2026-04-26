"""Tests for src/ui/error_formatter.py."""

from __future__ import annotations

import pytest

from src.ui.error_formatter import format_batch_summary, format_ingestion_error, format_refresh_error

# ---------------------------------------------------------------------------
# format_refresh_error — error_kind mapping
# ---------------------------------------------------------------------------


def test_refresh_error_not_found_uses_kind_message():
    msg = format_refresh_error("MC.PA", "not_found")
    assert "MC.PA" in msg
    assert "introuvable" in msg.lower()


def test_refresh_error_provider_error_uses_kind_message():
    msg = format_refresh_error("BNP.PA", "provider_error")
    assert "BNP.PA" in msg
    assert "indisponible" in msg.lower()


def test_refresh_error_data_inconsistent_uses_kind_message():
    msg = format_refresh_error("ALAMY.PA", "data_inconsistent")
    assert "ALAMY.PA" in msg
    assert "incohérentes" in msg.lower()


def test_refresh_error_none_kind_falls_back_to_stage():
    msg = format_refresh_error("MC.PA", None, stage="fetch")
    assert "MC.PA" in msg
    assert "récupération" in msg.lower()


def test_refresh_error_none_kind_none_stage_gives_generic():
    msg = format_refresh_error("MC.PA", None, stage=None)
    assert "MC.PA" in msg
    assert "erreur" in msg.lower()


def test_refresh_error_empty_ticker_still_produces_message():
    msg = format_refresh_error("", "not_found")
    assert "introuvable" in msg.lower()


def test_refresh_error_unknown_kind_falls_back_to_stage():
    msg = format_refresh_error("X.PA", "unknown_future_kind", stage="validate")
    assert "X.PA" in msg
    assert "validation" in msg.lower()


# ---------------------------------------------------------------------------
# format_ingestion_error — error_kind mapping
# ---------------------------------------------------------------------------


def test_ingestion_error_not_found():
    msg = format_ingestion_error("MC.PA", "not_found")
    assert "MC.PA" in msg
    assert "introuvable" in msg.lower()


def test_ingestion_error_provider_error():
    msg = format_ingestion_error("BNP", "provider_error")
    assert "indisponible" in msg.lower()


def test_ingestion_error_data_inconsistent():
    msg = format_ingestion_error("ALAMY.PA", "data_inconsistent")
    assert "incohérentes" in msg.lower()


def test_ingestion_error_validate_stage_returns_generic():
    # validate-stage errors are already handled by the dialog directly;
    # the formatter returns a generic fallback so nothing leaks raw text.
    msg = format_ingestion_error("BAD!!", None, stage="validate")
    assert msg  # non-empty
    assert "yahoo" not in msg.lower()
    assert "traceback" not in msg.lower()


def test_ingestion_error_none_kind_none_stage():
    msg = format_ingestion_error("MC.PA", None, stage=None)
    assert msg
    assert "yahoo" not in msg.lower()


# ---------------------------------------------------------------------------
# format_batch_summary — formatting
# ---------------------------------------------------------------------------


def test_batch_summary_all_success():
    msg = format_batch_summary("Univers actualisé", 5, 5, 0, [])
    assert "5/5" in msg
    assert "échec" not in msg


def test_batch_summary_some_failures():
    msg = format_batch_summary("Univers actualisé", 3, 5, 2, ["MC.PA", "BNP.PA"])
    assert "3/5" in msg
    assert "2 échec" in msg
    assert "MC.PA" in msg
    assert "BNP.PA" in msg


def test_batch_summary_truncates_to_three_tickers():
    failed = ["A", "B", "C", "D", "E"]
    msg = format_batch_summary("Univers actualisé", 0, 5, 5, failed)
    # Only first 3 visible
    assert "A" in msg
    assert "B" in msg
    assert "C" in msg
    assert "D" not in msg


def test_batch_summary_skips_empty_tickers():
    msg = format_batch_summary("Watchlist actualisée", 2, 3, 1, ["", "", ""])
    # Empty tickers should not appear but the failure count is still shown
    assert "1 échec" in msg


def test_batch_summary_ends_with_period():
    msg = format_batch_summary("Univers actualisé", 2, 2, 0, [])
    assert msg.endswith(".")


@pytest.mark.parametrize(
    "label",
    ["Univers actualisé", "Watchlist actualisée"],
)
def test_batch_summary_uses_provided_label(label):
    msg = format_batch_summary(label, 1, 1, 0, [])
    assert label in msg


# ---------------------------------------------------------------------------
# No raw technical text exposed (regression guard)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind",
    ["not_found", "provider_error", "data_inconsistent"],
)
def test_refresh_error_never_contains_raw_exc_words(kind):
    msg = format_refresh_error("MC.PA", kind)
    for forbidden in ("Exception", "Traceback", "yfinance", "HTTPError", "timeout"):
        assert forbidden not in msg
