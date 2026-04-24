from __future__ import annotations

_ZERO: float = 1e-9


def market_cap(price: float, shares_outstanding: float) -> float:
    return price * shares_outstanding


def enterprise_value(mkt_cap: float, net_debt: float) -> float:
    return mkt_cap + net_debt
