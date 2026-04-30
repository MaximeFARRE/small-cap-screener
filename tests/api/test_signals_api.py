"""Integration tests for the /api/signals endpoint."""

from fastapi.testclient import TestClient


class TestGetSignals:
    def test_returns_signals_schema(self, api_client: TestClient) -> None:
        response = api_client.get("/api/signals")
        assert response.status_code == 200
        data = response.json()
        assert "movers_up" in data
        assert "movers_down" in data
        assert "top_quality" in data
        assert "top_value" in data
        assert "has_snapshot" in data

    def test_no_snapshot_has_snapshot_false(self, api_client: TestClient) -> None:
        response = api_client.get("/api/signals")
        assert response.status_code == 200
        data = response.json()
        assert data["has_snapshot"] is False
        assert data["movers_up"] == []
        assert data["movers_down"] == []
