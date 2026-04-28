from __future__ import annotations

from datetime import date, datetime

from src.repositories.providers.base import (
    CompanyProfile,
    DividendData,
    ExecutiveData,
    HolderData,
    InsiderTransactionData,
    MarketData,
    PriceHistory,
    PriceRecord,
    SplitData,
)


def test_dto_creation_with_metadata():
    fetched_at = datetime.now()

    profile = CompanyProfile(
        ticker="TTE.PA",
        name="TotalEnergies",
        sector="Energy",
        industry="Oil & Gas Integrated",
        market="PAR",
        country="France",
        currency="EUR",
        website="https://totalenergies.com",
        source="yfinance",
        fetched_at=fetched_at,
    )
    market_data = MarketData(
        ticker="TTE.PA",
        current_price=55.2,
        previous_close=54.8,
        open=55.0,
        day_high=56.0,
        day_low=54.5,
        volume=420000,
        market_cap=120000000000.0,
        currency="EUR",
        source="yfinance",
        fetched_at=fetched_at,
    )
    price = PriceHistory(
        date=date(2024, 1, 2),
        open=50.0,
        high=52.0,
        low=49.0,
        close=51.5,
        adjusted_close=51.5,
        volume=100000,
        source="yfinance",
        fetched_at=fetched_at,
    )
    dividend = DividendData(
        ex_date=date(2024, 5, 1),
        amount=0.79,
        payment_date=None,
        source="yfinance",
        fetched_at=fetched_at,
    )
    split = SplitData(
        split_date=date(2020, 1, 10),
        ratio_from=1.0,
        ratio_to=2.0,
        source="yfinance",
        fetched_at=fetched_at,
    )
    holder = HolderData(
        ticker="TTE.PA",
        holder_type="institutional",
        holder_name="BlackRock",
        weight=0.08,
        source="yfinance",
        fetched_at=fetched_at,
    )
    insider = InsiderTransactionData(
        ticker="TTE.PA",
        insider_name="Jane Doe",
        relation="CFO",
        transaction_text="Sale",
        ownership="D",
        shares=10000.0,
        market_value=300000.0,
        source="yfinance",
        fetched_at=fetched_at,
    )
    executive = ExecutiveData(
        ticker="TTE.PA",
        name="John Leader",
        title="Chief Executive Officer",
        age=52,
        total_pay=1200000.0,
        source="yfinance",
        fetched_at=fetched_at,
    )

    assert profile.source == "yfinance"
    assert market_data.fetched_at == fetched_at
    assert price.source == "yfinance"
    assert dividend.fetched_at == fetched_at
    assert split.source == "yfinance"
    assert holder.source == "yfinance"
    assert insider.fetched_at == fetched_at
    assert executive.title == "Chief Executive Officer"


def test_dto_optional_fields_accept_none():
    profile = CompanyProfile(
        ticker="ABC.PA",
        name="Example",
        sector=None,
        industry=None,
        market=None,
        country=None,
        currency="EUR",
        website=None,
    )
    market_data = MarketData(
        ticker="ABC.PA",
        current_price=10.0,
        previous_close=None,
        open=None,
        day_high=None,
        day_low=None,
        volume=None,
        market_cap=None,
        currency=None,
    )
    price = PriceHistory(
        date=date(2024, 1, 1),
        open=None,
        high=None,
        low=None,
        close=10.0,
        adjusted_close=None,
        volume=None,
    )
    dividend = DividendData(ex_date=date(2024, 1, 1), amount=1.0, payment_date=None)
    split = SplitData(split_date=date(2024, 1, 1), ratio_from=1.0, ratio_to=2.0)

    assert profile.source is None and profile.fetched_at is None
    assert market_data.source is None and market_data.fetched_at is None
    assert price.source is None and price.fetched_at is None
    assert dividend.source is None and dividend.fetched_at is None
    assert split.source is None and split.fetched_at is None


def test_price_record_alias_keeps_type_compatibility():
    record = PriceRecord(
        date=date(2024, 1, 2),
        open=50.0,
        high=52.0,
        low=49.0,
        close=51.5,
        adjusted_close=51.5,
        volume=100000,
    )
    assert isinstance(record, PriceHistory)
