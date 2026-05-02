from __future__ import annotations

import math
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
    fcf_yield: float | None = None
    roe: float | None = None
    roic: float | None = None
    roce: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    revenue_growth: float | None = None
    ebitda_growth: float | None = None
    revenue_cagr_3y: float | None = None
    ebitda_cagr_3y: float | None = None
    net_income_growth: float | None = None
    fcf_growth: float | None = None
    gross_profit_growth: float | None = None
    net_debt_growth: float | None = None
    net_debt_to_ebitda: float | None = None
    current_ratio: float | None = None
    interest_coverage: float | None = None
    ps_ratio: float | None = None
    ev_sales: float | None = None
    fcf_margin: float | None = None
    cash_conversion_ratio: float | None = None
    asset_turnover: float | None = None
    # Backward-compatible metrics kept for existing services/scoring.
    roa: float | None = None
    ebit_margin: float | None = None
    ebitda_margin: float | None = None
    net_margin: float | None = None
    debt_to_equity: float | None = None


@dataclass
class RatioService:
    zero_threshold: float = _ZERO

    def compute_all(
        self,
        company_id: int,
        fiscal_year: int,
        price: float,
        stmt: FinancialStatement,
        previous_stmt: FinancialStatement | None = None,
        three_year_ago_stmt: FinancialStatement | None = None,
        *,
        gross_profit: float | None = None,
        current_assets: float | None = None,
        current_liabilities: float | None = None,
        interest_expense: float | None = None,
        invested_capital: float | None = None,
        tax_rate: float = 0.25,
    ) -> CompanyRatios:
        market_cap_value = self.market_cap(price, stmt.shares_outstanding or 0.0)
        enterprise_value_value = self.enterprise_value(market_cap_value, stmt.net_debt or 0.0)
        return CompanyRatios(
            company_id=company_id,
            fiscal_year=fiscal_year,
            price=price,
            mkt_cap=market_cap_value,
            ev=enterprise_value_value,
            pe_ratio=self.pe_ratio(price, stmt.net_income, stmt.shares_outstanding),
            pb_ratio=self.pb_ratio(market_cap_value, stmt.total_equity),
            ev_ebitda=self.ev_ebitda(enterprise_value_value, stmt.ebitda),
            ev_ebit=self.ev_ebit(enterprise_value_value, stmt.ebit),
            price_to_fcf=self.price_to_fcf(market_cap_value, stmt.free_cash_flow),
            fcf_yield=self.fcf_yield(stmt.free_cash_flow, market_cap_value),
            roe=self.roe(stmt.net_income, stmt.total_equity),
            roic=self.roic(
                ebit=stmt.ebit,
                invested_capital=invested_capital,
                total_equity=stmt.total_equity,
                net_debt=stmt.net_debt,
                total_debt=stmt.total_debt,
                tax_rate=tax_rate,
            ),
            roce=self.roce(stmt.ebit, stmt.total_assets, current_liabilities),
            gross_margin=self.gross_margin(gross_profit, stmt.revenue),
            operating_margin=self.operating_margin(stmt.ebit, stmt.revenue),
            revenue_growth=self.revenue_growth(
                current_revenue=stmt.revenue,
                previous_revenue=previous_stmt.revenue if previous_stmt is not None else None,
            ),
            ebitda_growth=self.ebitda_growth(
                current_ebitda=stmt.ebitda,
                previous_ebitda=previous_stmt.ebitda if previous_stmt is not None else None,
            ),
            revenue_cagr_3y=self.revenue_cagr_3y(
                current_revenue=stmt.revenue,
                three_year_ago_revenue=three_year_ago_stmt.revenue if three_year_ago_stmt is not None else None,
            ),
            ebitda_cagr_3y=self.ebitda_cagr_3y(
                current_ebitda=stmt.ebitda,
                three_year_ago_ebitda=three_year_ago_stmt.ebitda if three_year_ago_stmt is not None else None,
            ),
            net_income_growth=self.net_income_growth(
                current_net_income=stmt.net_income,
                previous_net_income=previous_stmt.net_income if previous_stmt is not None else None,
            ),
            fcf_growth=self.fcf_growth(
                current_fcf=stmt.free_cash_flow,
                previous_fcf=previous_stmt.free_cash_flow if previous_stmt is not None else None,
            ),
            gross_profit_growth=self.gross_profit_growth(
                current_gross_profit=stmt.gross_profit,
                previous_gross_profit=previous_stmt.gross_profit if previous_stmt is not None else None,
            ),
            net_debt_growth=self.net_debt_growth(
                current_net_debt=stmt.net_debt,
                previous_net_debt=previous_stmt.net_debt if previous_stmt is not None else None,
            ),
            net_debt_to_ebitda=self.net_debt_to_ebitda(stmt.net_debt, stmt.ebitda),
            current_ratio=self.current_ratio(current_assets, current_liabilities),
            interest_coverage=self.interest_coverage(stmt.ebit, interest_expense),
            ps_ratio=self.ps_ratio(market_cap_value, stmt.revenue),
            ev_sales=self.ev_sales(enterprise_value_value, stmt.revenue),
            fcf_margin=self.fcf_margin(stmt.free_cash_flow, stmt.revenue),
            cash_conversion_ratio=self.cash_conversion_ratio(stmt.free_cash_flow, stmt.net_income),
            asset_turnover=self.asset_turnover(stmt.revenue, stmt.total_assets),
            # Backward-compatible aliases/legacy outputs.
            roa=self.roa(stmt.net_income, stmt.total_assets),
            ebit_margin=self.ebit_margin(stmt.ebit, stmt.revenue),
            ebitda_margin=self.ebitda_margin(stmt.ebitda, stmt.revenue),
            net_margin=self.net_margin(stmt.net_income, stmt.revenue),
            debt_to_equity=self.debt_to_equity(stmt.total_debt, stmt.total_equity),
        )

    def market_cap(self, price: float, shares_outstanding: float) -> float:
        if not _is_finite(price) or not _is_finite(shares_outstanding):
            return 0.0
        return price * shares_outstanding

    def enterprise_value(self, mkt_cap: float, net_debt: float) -> float:
        if not _is_finite(mkt_cap) or not _is_finite(net_debt):
            return 0.0
        return mkt_cap + net_debt

    def pe_ratio(
        self,
        price: float,
        net_income: float | None,
        shares_outstanding: float | None,
    ) -> float | None:
        eps = _safe_div(net_income, shares_outstanding)
        if eps is None:
            return None
        return _safe_div(price, eps)

    def pb_ratio(self, mkt_cap: float, total_equity: float | None) -> float | None:
        return _safe_div(mkt_cap, total_equity, positive_denominator=True)

    def ev_ebitda(self, ev: float, ebitda: float | None) -> float | None:
        return _safe_div(ev, ebitda, positive_denominator=True)

    def ev_ebit(self, ev: float, ebit: float | None) -> float | None:
        return _safe_div(ev, ebit, positive_denominator=True)

    def price_to_fcf(self, mkt_cap: float, free_cash_flow: float | None) -> float | None:
        return _safe_div(mkt_cap, free_cash_flow)

    def fcf_yield(self, free_cash_flow: float | None, mkt_cap: float | None) -> float | None:
        return _safe_div(free_cash_flow, mkt_cap, positive_denominator=True)

    def roe(self, net_income: float | None, total_equity: float | None) -> float | None:
        return _safe_div(net_income, total_equity, positive_denominator=True)

    def roic(
        self,
        *,
        ebit: float | None,
        invested_capital: float | None,
        total_equity: float | None,
        net_debt: float | None,
        total_debt: float | None,
        tax_rate: float = 0.25,
    ) -> float | None:
        if ebit is None or not _is_finite(ebit):
            return None
        nopat = ebit * (1.0 - tax_rate)
        cap = invested_capital
        if cap is None:
            if total_equity is not None and net_debt is not None:
                cap = total_equity + net_debt
            elif total_equity is not None and total_debt is not None:
                cap = total_equity + total_debt
        return _safe_div(nopat, cap, positive_denominator=True)

    def roce(
        self,
        ebit: float | None,
        total_assets: float | None,
        current_liabilities: float | None,
    ) -> float | None:
        if total_assets is None or current_liabilities is None:
            return None
        capital_employed = total_assets - current_liabilities
        return _safe_div(ebit, capital_employed, positive_denominator=True)

    def gross_margin(self, gross_profit: float | None, revenue: float | None) -> float | None:
        return _safe_div(gross_profit, revenue, positive_denominator=True)

    def operating_margin(self, ebit: float | None, revenue: float | None) -> float | None:
        return _safe_div(ebit, revenue, positive_denominator=True)

    def revenue_growth(self, current_revenue: float | None, previous_revenue: float | None) -> float | None:
        if current_revenue is None or previous_revenue is None:
            return None
        if not _is_finite(current_revenue) or not _is_finite(previous_revenue):
            return None
        if previous_revenue <= self.zero_threshold:
            return None
        return (current_revenue - previous_revenue) / previous_revenue

    def ebitda_growth(self, current_ebitda: float | None, previous_ebitda: float | None) -> float | None:
        if current_ebitda is None or previous_ebitda is None:
            return None
        if not _is_finite(current_ebitda) or not _is_finite(previous_ebitda):
            return None
        if previous_ebitda <= self.zero_threshold:
            return None
        return (current_ebitda - previous_ebitda) / previous_ebitda

    def ps_ratio(self, mkt_cap: float, revenue: float | None) -> float | None:
        return _safe_div(mkt_cap, revenue, positive_denominator=True)

    def ev_sales(self, ev: float, revenue: float | None) -> float | None:
        return _safe_div(ev, revenue, positive_denominator=True)

    def fcf_margin(self, free_cash_flow: float | None, revenue: float | None) -> float | None:
        return _safe_div(free_cash_flow, revenue, positive_denominator=True)

    def cash_conversion_ratio(self, free_cash_flow: float | None, net_income: float | None) -> float | None:
        return _safe_div(free_cash_flow, net_income)

    def asset_turnover(self, revenue: float | None, total_assets: float | None) -> float | None:
        return _safe_div(revenue, total_assets, positive_denominator=True)

    def net_income_growth(
        self,
        current_net_income: float | None,
        previous_net_income: float | None,
    ) -> float | None:
        return self._yoy_growth(current_net_income, previous_net_income)

    def fcf_growth(
        self,
        current_fcf: float | None,
        previous_fcf: float | None,
    ) -> float | None:
        return self._yoy_growth(current_fcf, previous_fcf)

    def gross_profit_growth(
        self,
        current_gross_profit: float | None,
        previous_gross_profit: float | None,
    ) -> float | None:
        return self._yoy_growth(current_gross_profit, previous_gross_profit)

    def net_debt_growth(
        self,
        current_net_debt: float | None,
        previous_net_debt: float | None,
    ) -> float | None:
        if current_net_debt is None or previous_net_debt is None:
            return None
        if not _is_finite(current_net_debt) or not _is_finite(previous_net_debt):
            return None
        abs_base = abs(previous_net_debt)
        if abs_base < self.zero_threshold:
            return None
        return (current_net_debt - previous_net_debt) / abs_base

    def _yoy_growth(self, current: float | None, previous: float | None) -> float | None:
        if current is None or previous is None:
            return None
        if not _is_finite(current) or not _is_finite(previous):
            return None
        if previous <= self.zero_threshold:
            return None
        return (current - previous) / previous

    def revenue_cagr_3y(
        self,
        current_revenue: float | None,
        three_year_ago_revenue: float | None,
    ) -> float | None:
        return self._cagr_3y(current_revenue, three_year_ago_revenue)

    def ebitda_cagr_3y(
        self,
        current_ebitda: float | None,
        three_year_ago_ebitda: float | None,
    ) -> float | None:
        return self._cagr_3y(current_ebitda, three_year_ago_ebitda)

    def _cagr_3y(self, current: float | None, three_years_ago: float | None) -> float | None:
        if current is None or three_years_ago is None:
            return None
        if not _is_finite(current) or not _is_finite(three_years_ago):
            return None
        if three_years_ago <= self.zero_threshold:
            return None
        return (current / three_years_ago) ** (1.0 / 3.0) - 1.0

    def net_debt_to_ebitda(self, net_debt: float | None, ebitda: float | None) -> float | None:
        return _safe_div(net_debt, ebitda, positive_denominator=True)

    def current_ratio(self, current_assets: float | None, current_liabilities: float | None) -> float | None:
        return _safe_div(current_assets, current_liabilities, positive_denominator=True)

    def interest_coverage(self, ebit: float | None, interest_expense: float | None) -> float | None:
        return _safe_div(ebit, interest_expense, positive_denominator=True)

    # Backward-compatible helpers.
    def roa(self, net_income: float | None, total_assets: float | None) -> float | None:
        return _safe_div(net_income, total_assets, positive_denominator=True)

    def ebit_margin(self, ebit: float | None, revenue: float | None) -> float | None:
        return self.operating_margin(ebit, revenue)

    def ebitda_margin(self, ebitda: float | None, revenue: float | None) -> float | None:
        return _safe_div(ebitda, revenue, positive_denominator=True)

    def net_margin(self, net_income: float | None, revenue: float | None) -> float | None:
        return _safe_div(net_income, revenue, positive_denominator=True)

    def debt_to_equity(self, total_debt: float | None, total_equity: float | None) -> float | None:
        return _safe_div(total_debt, total_equity, positive_denominator=True)


def _is_finite(value: float | int | None) -> bool:
    return value is not None and math.isfinite(float(value))


def _safe_div(
    numerator: float | int | None,
    denominator: float | int | None,
    *,
    positive_denominator: bool = False,
) -> float | None:
    if not _is_finite(numerator) or not _is_finite(denominator):
        return None
    denominator_value = float(denominator)
    if abs(denominator_value) < _ZERO:
        return None
    if positive_denominator and denominator_value <= 0:
        return None
    return float(numerator) / denominator_value


_SERVICE = RatioService()


def compute_all(
    company_id: int,
    fiscal_year: int,
    price: float,
    stmt: FinancialStatement,
    previous_stmt: FinancialStatement | None = None,
    three_year_ago_stmt: FinancialStatement | None = None,
    *,
    gross_profit: float | None = None,
    current_assets: float | None = None,
    current_liabilities: float | None = None,
    interest_expense: float | None = None,
    invested_capital: float | None = None,
    tax_rate: float = 0.25,
) -> CompanyRatios:
    return _SERVICE.compute_all(
        company_id=company_id,
        fiscal_year=fiscal_year,
        price=price,
        stmt=stmt,
        previous_stmt=previous_stmt,
        three_year_ago_stmt=three_year_ago_stmt,
        gross_profit=gross_profit,
        current_assets=current_assets,
        current_liabilities=current_liabilities,
        interest_expense=interest_expense,
        invested_capital=invested_capital,
        tax_rate=tax_rate,
    )


def market_cap(price: float, shares_outstanding: float) -> float:
    return _SERVICE.market_cap(price, shares_outstanding)


def enterprise_value(mkt_cap: float, net_debt: float) -> float:
    return _SERVICE.enterprise_value(mkt_cap, net_debt)


def pe_ratio(price: float, net_income: float | None, shares_outstanding: float | None) -> float | None:
    return _SERVICE.pe_ratio(price, net_income, shares_outstanding)


def pb_ratio(mkt_cap: float, total_equity: float | None) -> float | None:
    return _SERVICE.pb_ratio(mkt_cap, total_equity)


def ev_ebitda(ev: float, ebitda: float | None) -> float | None:
    return _SERVICE.ev_ebitda(ev, ebitda)


def ev_ebit(ev: float, ebit: float | None) -> float | None:
    return _SERVICE.ev_ebit(ev, ebit)


def price_to_fcf(mkt_cap: float, free_cash_flow: float | None) -> float | None:
    return _SERVICE.price_to_fcf(mkt_cap, free_cash_flow)


def fcf_yield(free_cash_flow: float | None, mkt_cap: float | None) -> float | None:
    return _SERVICE.fcf_yield(free_cash_flow, mkt_cap)


def roe(net_income: float | None, total_equity: float | None) -> float | None:
    return _SERVICE.roe(net_income, total_equity)


def roic(
    *,
    ebit: float | None,
    invested_capital: float | None,
    total_equity: float | None,
    net_debt: float | None,
    total_debt: float | None,
    tax_rate: float = 0.25,
) -> float | None:
    return _SERVICE.roic(
        ebit=ebit,
        invested_capital=invested_capital,
        total_equity=total_equity,
        net_debt=net_debt,
        total_debt=total_debt,
        tax_rate=tax_rate,
    )


def roce(ebit: float | None, total_assets: float | None, current_liabilities: float | None) -> float | None:
    return _SERVICE.roce(ebit, total_assets, current_liabilities)


def gross_margin(gross_profit: float | None, revenue: float | None) -> float | None:
    return _SERVICE.gross_margin(gross_profit, revenue)


def operating_margin(ebit: float | None, revenue: float | None) -> float | None:
    return _SERVICE.operating_margin(ebit, revenue)


def revenue_growth(current_revenue: float | None, previous_revenue: float | None) -> float | None:
    return _SERVICE.revenue_growth(current_revenue, previous_revenue)


def ebitda_growth(current_ebitda: float | None, previous_ebitda: float | None) -> float | None:
    return _SERVICE.ebitda_growth(current_ebitda, previous_ebitda)


def net_debt_to_ebitda(net_debt: float | None, ebitda: float | None) -> float | None:
    return _SERVICE.net_debt_to_ebitda(net_debt, ebitda)


def current_ratio(current_assets: float | None, current_liabilities: float | None) -> float | None:
    return _SERVICE.current_ratio(current_assets, current_liabilities)


def interest_coverage(ebit: float | None, interest_expense: float | None) -> float | None:
    return _SERVICE.interest_coverage(ebit, interest_expense)


def roa(net_income: float | None, total_assets: float | None) -> float | None:
    return _SERVICE.roa(net_income, total_assets)


def ebit_margin(ebit: float | None, revenue: float | None) -> float | None:
    return _SERVICE.ebit_margin(ebit, revenue)


def ebitda_margin(ebitda: float | None, revenue: float | None) -> float | None:
    return _SERVICE.ebitda_margin(ebitda, revenue)


def net_margin(net_income: float | None, revenue: float | None) -> float | None:
    return _SERVICE.net_margin(net_income, revenue)


def debt_to_equity(total_debt: float | None, total_equity: float | None) -> float | None:
    return _SERVICE.debt_to_equity(total_debt, total_equity)


def ps_ratio(mkt_cap: float, revenue: float | None) -> float | None:
    return _SERVICE.ps_ratio(mkt_cap, revenue)


def ev_sales(ev: float, revenue: float | None) -> float | None:
    return _SERVICE.ev_sales(ev, revenue)


def fcf_margin(free_cash_flow: float | None, revenue: float | None) -> float | None:
    return _SERVICE.fcf_margin(free_cash_flow, revenue)


def cash_conversion_ratio(free_cash_flow: float | None, net_income: float | None) -> float | None:
    return _SERVICE.cash_conversion_ratio(free_cash_flow, net_income)


def asset_turnover(revenue: float | None, total_assets: float | None) -> float | None:
    return _SERVICE.asset_turnover(revenue, total_assets)


def net_income_growth(current_net_income: float | None, previous_net_income: float | None) -> float | None:
    return _SERVICE.net_income_growth(current_net_income, previous_net_income)


def fcf_growth(current_fcf: float | None, previous_fcf: float | None) -> float | None:
    return _SERVICE.fcf_growth(current_fcf, previous_fcf)


def gross_profit_growth(current_gross_profit: float | None, previous_gross_profit: float | None) -> float | None:
    return _SERVICE.gross_profit_growth(current_gross_profit, previous_gross_profit)


def net_debt_growth(current_net_debt: float | None, previous_net_debt: float | None) -> float | None:
    return _SERVICE.net_debt_growth(current_net_debt, previous_net_debt)


def revenue_cagr_3y(current_revenue: float | None, three_year_ago_revenue: float | None) -> float | None:
    return _SERVICE.revenue_cagr_3y(current_revenue, three_year_ago_revenue)


def ebitda_cagr_3y(current_ebitda: float | None, three_year_ago_ebitda: float | None) -> float | None:
    return _SERVICE.ebitda_cagr_3y(current_ebitda, three_year_ago_ebitda)
