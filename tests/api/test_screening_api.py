"""Integration tests for the /api/screening endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.models.company import Company


def _seed_company(db_session, ticker: str = "TEST.PA", name: str = "Test Corp") -> Company:
    company = Company(
        ticker=ticker,
        name=name,
        country="France",
        sector="Technology",
        currency="EUR",
        market_cap=500_000_000.0,
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


class TestGetUniverse:
    def test_returns_empty_list_when_no_companies(self, api_client: TestClient) -> None:
        response = api_client.get("/api/screening/universe")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_list_schema(self, api_client: TestClient, db_session) -> None:
        _seed_company(db_session)
        response = api_client.get("/api/screening/universe")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_sector_filter(self, api_client: TestClient, db_session) -> None:
        _seed_company(db_session, ticker="A.PA", name="Tech Corp")
        _seed_company(db_session, ticker="B.PA", name="Bank Corp")
        # Update sector for second company
        bank = db_session.query(Company).filter_by(ticker="B.PA").first()
        bank.sector = "Financials"
        db_session.commit()

        response = api_client.get("/api/screening/universe?sector=Technology")
        assert response.status_code == 200
        data = response.json()
        assert all(c["sector"] == "Technology" for c in data)


class TestFilterUniverse:
    def test_post_with_empty_filters_returns_all(self, api_client: TestClient, db_session) -> None:
        _seed_company(db_session)
        response = api_client.post("/api/screening/universe/filter", json={})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_invalid_sort_by_returns_unfiltered(self, api_client: TestClient) -> None:
        response = api_client.post(
            "/api/screening/universe/filter",
            json={"sort_by": "rank", "top_n": 5},
        )
        assert response.status_code == 200


class TestSnapshots:
    def test_list_snapshots_empty(self, api_client: TestClient) -> None:
        response = api_client.get("/api/screening/snapshots")
        assert response.status_code == 200
        assert response.json() == []

    def test_save_snapshot(self, api_client: TestClient) -> None:
        response = api_client.post(
            "/api/screening/snapshots",
            json={"name": "test snapshot", "filters": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test snapshot"
        assert "snapshot_id" in data

    def test_get_snapshot_not_found(self, api_client: TestClient) -> None:
        response = api_client.get("/api/screening/snapshots/9999")
        assert response.status_code == 404
