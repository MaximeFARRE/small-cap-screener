"""Integration tests for the /api/companies endpoints."""

from fastapi.testclient import TestClient

from src.models.company import Company


def _seed_company(db_session, ticker: str = "TEST.PA") -> Company:
    company = Company(
        ticker=ticker,
        name="Test Corp",
        country="France",
        sector="Technology",
        currency="EUR",
        market_cap=500_000_000.0,
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


class TestGetCompanyDetail:
    def test_unknown_ticker_returns_404(self, api_client: TestClient) -> None:
        response = api_client.get("/api/companies/UNKNOWN.PA")
        assert response.status_code == 404

    def test_known_ticker_returns_detail_schema(self, api_client: TestClient, db_session) -> None:
        _seed_company(db_session)
        response = api_client.get("/api/companies/TEST.PA")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "TEST.PA"
        assert data["name"] == "Test Corp"
        assert "historical_fundamentals" in data
        assert "management_team" in data

    def test_response_has_required_ratio_fields(self, api_client: TestClient, db_session) -> None:
        _seed_company(db_session)
        response = api_client.get("/api/companies/TEST.PA")
        assert response.status_code == 200
        data = response.json()
        for field in ("pe_ratio", "ev_ebitda", "roe", "roic", "revenue_growth"):
            assert field in data


class TestGetCompanyScore:
    def test_unknown_ticker_returns_404(self, api_client: TestClient) -> None:
        response = api_client.get("/api/companies/UNKNOWN.PA/score")
        assert response.status_code == 404

    def test_score_schema_structure(self, api_client: TestClient, db_session) -> None:
        _seed_company(db_session)
        response = api_client.get("/api/companies/TEST.PA/score")
        assert response.status_code == 200
        data = response.json()
        assert "total_score" in data
        assert "quality" in data
        assert "value" in data
        assert "growth" in data
        assert "risk" in data
        assert isinstance(data["positive_drivers"], list)
        assert isinstance(data["negative_drivers"], list)
        assert isinstance(data["weights"], list)


class TestGetCompanyPeers:
    def test_unknown_ticker_returns_404(self, api_client: TestClient) -> None:
        response = api_client.get("/api/companies/UNKNOWN.PA/peers")
        assert response.status_code == 404

    def test_peers_schema_structure(self, api_client: TestClient, db_session) -> None:
        _seed_company(db_session)
        response = api_client.get("/api/companies/TEST.PA/peers")
        assert response.status_code == 200
        data = response.json()
        assert "sector" in data
        assert "peer_rows" in data
        assert "metrics" in data
        assert "analyst_assessment" in data
