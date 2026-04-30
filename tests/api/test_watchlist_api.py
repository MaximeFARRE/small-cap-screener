"""Integration tests for the /api/watchlist endpoints."""

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


class TestListWatchlist:
    def test_empty_watchlist(self, api_client: TestClient) -> None:
        response = api_client.get("/api/watchlist")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_list_schema(self, api_client: TestClient, db_session) -> None:
        _seed_company(db_session)
        api_client.post("/api/watchlist/TEST.PA", json={})

        response = api_client.get("/api/watchlist")
        assert response.status_code == 200
        entries = response.json()
        assert len(entries) == 1
        assert entries[0]["ticker"] == "TEST.PA"


class TestAddRemoveWatchlist:
    def test_add_unknown_ticker_returns_404(self, api_client: TestClient) -> None:
        response = api_client.post("/api/watchlist/UNKNOWN.PA", json={})
        assert response.status_code == 404

    def test_add_then_remove(self, api_client: TestClient, db_session) -> None:
        _seed_company(db_session)

        add_response = api_client.post("/api/watchlist/TEST.PA", json={})
        assert add_response.status_code == 200

        remove_response = api_client.delete("/api/watchlist/TEST.PA")
        assert remove_response.status_code == 204

        list_response = api_client.get("/api/watchlist")
        assert list_response.json() == []

    def test_remove_unknown_ticker_returns_404(self, api_client: TestClient) -> None:
        response = api_client.delete("/api/watchlist/UNKNOWN.PA")
        assert response.status_code == 404

    def test_remove_not_in_watchlist_returns_404(self, api_client: TestClient, db_session) -> None:
        _seed_company(db_session)
        response = api_client.delete("/api/watchlist/TEST.PA")
        assert response.status_code == 404


class TestUpdateMemo:
    def test_update_memo_on_unknown_ticker_returns_404(self, api_client: TestClient) -> None:
        response = api_client.patch(
            "/api/watchlist/UNKNOWN.PA/memo",
            json={"investment_thesis": "great company"},
        )
        assert response.status_code == 404

    def test_update_memo_persists(self, api_client: TestClient, db_session) -> None:
        _seed_company(db_session)
        api_client.post("/api/watchlist/TEST.PA", json={})

        patch_response = api_client.patch(
            "/api/watchlist/TEST.PA/memo",
            json={
                "investment_thesis": "Strong competitive moat",
                "key_risks": "Regulatory risk",
                "catalysts": None,
                "valuation_notes": None,
                "next_action": None,
            },
        )
        assert patch_response.status_code == 200
        data = patch_response.json()
        assert data["investment_thesis"] == "Strong competitive moat"


class TestUpdateStatus:
    def test_update_status(self, api_client: TestClient, db_session) -> None:
        _seed_company(db_session)
        api_client.post("/api/watchlist/TEST.PA", json={})

        response = api_client.patch(
            "/api/watchlist/TEST.PA/status",
            json={"status": "conviction"},
        )
        assert response.status_code == 204
