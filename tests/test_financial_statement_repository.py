from src.models.company import Company
from src.models.financial_statement import FinancialStatement, PeriodType
from src.repositories import company_repository, financial_statement_repository


def _make_company(session) -> Company:
    return company_repository.create(
        session,
        Company(isin="FR0000120271", name="TotalEnergies", currency="EUR"),
    )


def test_create_and_get_by_id(db_session):
    company = _make_company(db_session)
    stmt = FinancialStatement(
        company_id=company.id, fiscal_year=2023, revenue=200_000_000.0
    )
    financial_statement_repository.create(db_session, stmt)
    result = financial_statement_repository.get_by_id(db_session, stmt.id)
    assert result is not None
    assert result.fiscal_year == 2023
    assert result.revenue == 200_000_000.0


def test_get_by_company_ordered_desc(db_session):
    company = _make_company(db_session)
    financial_statement_repository.create(
        db_session,
        FinancialStatement(company_id=company.id, fiscal_year=2022),
    )
    financial_statement_repository.create(
        db_session,
        FinancialStatement(company_id=company.id, fiscal_year=2023),
    )
    results = financial_statement_repository.get_by_company(db_session, company.id)
    assert len(results) == 2
    assert results[0].fiscal_year == 2023


def test_get_by_company_empty(db_session):
    company = _make_company(db_session)
    assert financial_statement_repository.get_by_company(db_session, company.id) == []


def test_get_by_company_and_year(db_session):
    company = _make_company(db_session)
    financial_statement_repository.create(
        db_session,
        FinancialStatement(
            company_id=company.id,
            fiscal_year=2023,
            period_type=PeriodType.ANNUAL,
        ),
    )
    result = financial_statement_repository.get_by_company_and_year(
        db_session, company.id, 2023
    )
    assert result is not None
    assert result.period_type == PeriodType.ANNUAL


def test_get_by_company_and_year_not_found(db_session):
    company = _make_company(db_session)
    assert (
        financial_statement_repository.get_by_company_and_year(
            db_session, company.id, 2020
        )
        is None
    )


def test_delete(db_session):
    company = _make_company(db_session)
    stmt = financial_statement_repository.create(
        db_session, FinancialStatement(company_id=company.id, fiscal_year=2023)
    )
    assert financial_statement_repository.delete(db_session, stmt.id) is True
    assert financial_statement_repository.get_by_id(db_session, stmt.id) is None


def test_delete_nonexistent(db_session):
    assert financial_statement_repository.delete(db_session, 9999) is False
