from __future__ import annotations

_ZERO: float = 1e-9


def market_cap(price: float, shares_outstanding: float) -> float:
    return price * shares_outstanding


def enterprise_value(mkt_cap: float, net_debt: float) -> float:
    return mkt_cap + net_debt


def pe_ratio(
    price: float,
    net_income: float | None,
    shares_outstanding: float | None,
) -> float | None:
    if net_income is None or shares_outstanding is None:
        return None
    if abs(shares_outstanding) < _ZERO:
        return None
    eps = net_income / shares_outstanding
    if abs(eps) < _ZERO:
        return None
    return price / eps


def pb_ratio(mkt_cap: float, total_equity: float | None) -> float | None:
    if total_equity is None or abs(total_equity) < _ZERO:
        return None
    return mkt_cap / total_equity


def ev_ebitda(ev: float, ebitda: float | None) -> float | None:
    if ebitda is None or abs(ebitda) < _ZERO:
        return None
    return ev / ebitda


def ev_ebit(ev: float, ebit: float | None) -> float | None:
    if ebit is None or abs(ebit) < _ZERO:
        return None
    return ev / ebit


def price_to_fcf(mkt_cap: float, free_cash_flow: float | None) -> float | None:
    if free_cash_flow is None or abs(free_cash_flow) < _ZERO:
        return None
    return mkt_cap / free_cash_flow


def roe(net_income: float | None, total_equity: float | None) -> float | None:
    if net_income is None or total_equity is None or abs(total_equity) < _ZERO:
        return None
    return net_income / total_equity


def roa(net_income: float | None, total_assets: float | None) -> float | None:
    if net_income is None or total_assets is None or abs(total_assets) < _ZERO:
        return None
    return net_income / total_assets


def ebit_margin(ebit: float | None, revenue: float | None) -> float | None:
    if ebit is None or revenue is None or abs(revenue) < _ZERO:
        return None
    return ebit / revenue


def ebitda_margin(ebitda: float | None, revenue: float | None) -> float | None:
    if ebitda is None or revenue is None or abs(revenue) < _ZERO:
        return None
    return ebitda / revenue


def net_margin(net_income: float | None, revenue: float | None) -> float | None:
    if net_income is None or revenue is None or abs(revenue) < _ZERO:
        return None
    return net_income / revenue


def debt_to_equity(total_debt: float | None, total_equity: float | None) -> float | None:
    if total_debt is None or total_equity is None or abs(total_equity) < _ZERO:
        return None
    return total_debt / total_equity


def net_debt_to_ebitda(net_debt: float | None, ebitda: float | None) -> float | None:
    if net_debt is None or ebitda is None or abs(ebitda) < _ZERO:
        return None
    return net_debt / ebitda
