from __future__ import annotations

from dataclasses import dataclass

from src.models.financial_statement import FinancialStatement

_ZERO: float = 1e-9


@dataclass
class CompanyRatios:
    company_id: int
    fiscal_year: int
    price: float
    mkt_cap: float
    ev: float
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    ev_ebitda: float | None = None
    ev_ebit: float | None = None
    price_to_fcf: float | None = None
    roe: float | None = None
    roa: float | None = None
    ebit_margin: float | None = None
    ebitda_margin: float | None = None
    net_margin: float | None = None
    debt_to_equity: float | None = None
    net_debt_to_ebitda: float | None = None


def compute_all(
    company_id: int,
    fiscal_year: int,
    price: float,
    stmt: FinancialStatement,
) -> CompanyRatios:
    mkt = market_cap(price, stmt.shares_outstanding or 0.0)
    ev = enterprise_value(mkt, stmt.net_debt or 0.0)
    return CompanyRatios(
        company_id=company_id,
        fiscal_year=fiscal_year,
        price=price,
        mkt_cap=mkt,
        ev=ev,
        pe_ratio=pe_ratio(price, stmt.net_income, stmt.shares_outstanding),
        pb_ratio=pb_ratio(mkt, stmt.total_equity),
        ev_ebitda=ev_ebitda(ev, stmt.ebitda),
        ev_ebit=ev_ebit(ev, stmt.ebit),
        price_to_fcf=price_to_fcf(mkt, stmt.free_cash_flow),
        roe=roe(stmt.net_income, stmt.total_equity),
        roa=roa(stmt.net_income, stmt.total_assets),
        ebit_margin=ebit_margin(stmt.ebit, stmt.revenue),
        ebitda_margin=ebitda_margin(stmt.ebitda, stmt.revenue),
        net_margin=net_margin(stmt.net_income, stmt.revenue),
        debt_to_equity=debt_to_equity(stmt.total_debt, stmt.total_equity),
        net_debt_to_ebitda=net_debt_to_ebitda(stmt.net_debt, stmt.ebitda),
    )


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


def debt_to_equity(
    total_debt: float | None, total_equity: float | None
) -> float | None:
    if total_debt is None or total_equity is None or abs(total_equity) < _ZERO:
        return None
    return total_debt / total_equity


def net_debt_to_ebitda(net_debt: float | None, ebitda: float | None) -> float | None:
    if net_debt is None or ebitda is None or abs(ebitda) < _ZERO:
        return None
    return net_debt / ebitda
