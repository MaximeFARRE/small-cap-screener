from __future__ import annotations

import pytest

from src.repositories.euronext_discovery_repository import (
    EuronextResponseError,
    discover_french_listed_companies,
)


class _FakeResponse:
    def __init__(self, *, json_payload: dict | None = None, text_payload: str = "", status_code: int = 200) -> None:
        self._json_payload = json_payload
        self._text_payload = text_payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http status {self.status_code}")

    def json(self) -> dict:
        if self._json_payload is None:
            raise ValueError("no json")
        return self._json_payload

    @property
    def text(self) -> str:
        return self._text_payload


class _FakeClient:
    def __init__(self, post_payloads: list[dict], csv_payload: str = "") -> None:
        self._post_payloads = list(post_payloads)
        self._csv_payload = csv_payload
        self.post_calls: list[dict] = []
        self.get_calls: list[str] = []

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def post(self, url: str, data: dict) -> _FakeResponse:
        self.post_calls.append(data)
        if not self._post_payloads:
            raise AssertionError("unexpected POST call")
        return _FakeResponse(json_payload=self._post_payloads.pop(0))

    def get(self, url: str) -> _FakeResponse:
        self.get_calls.append(url)
        return _FakeResponse(text_payload=self._csv_payload)


def test_discover_french_listed_companies_handles_post_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    first_page = {
        "iTotalDisplayRecords": 150,
        "aaData": [
            [
                "",
                '<a href="/en/product/equities/FR0013341781-ALXP" data-order="2CRSI">2CRSI</a>',
                "FR0013341781",
                "AL2SI",
                '<div class="nowrap pointer" title="Euronext Growth Paris">ALXP</div>',
                '<div class="text-right pd_currency_es">EUR <span class="pd_last_price_es">37.70</span></div>',
                '<div class="text-right pd_percent"><span class=red>-6.45%</span></div>',
                (
                    '<div class="text-right pointer tooltipDesign">14:47 CEST'
                    '<span class="tooltiptext">28 Apr 2026</span></div>'
                ),
            ]
        ],
    }
    second_page = {
        "iTotalDisplayRecords": 150,
        "aaData": [
            [
                "",
                '<a href="/en/product/equities/FR0000120271-XPAR" data-order="TotalEnergies">TTE</a>',
                "FR0000120271",
                "TTE",
                '<div class="nowrap pointer" title="Euronext Paris">XPAR</div>',
                '<div class="text-right pd_currency_es">EUR <span class="pd_last_price_es">55.10</span></div>',
                '<div class="text-right pd_percent"><span class=red>-1.10%</span></div>',
                (
                    '<div class="text-right pointer tooltipDesign">14:47 CEST'
                    '<span class="tooltiptext">28 Apr 2026</span></div>'
                ),
            ]
        ],
    }
    fake_client = _FakeClient(post_payloads=[first_page, second_page])
    monkeypatch.setattr(
        "src.repositories.euronext_discovery_repository.httpx.Client",
        lambda **kwargs: fake_client,
    )

    entries = discover_french_listed_companies(page_size=100)

    assert len(entries) == 2
    assert {entry.ticker for entry in entries} == {"AL2SI.PA", "TTE.PA"}
    assert {entry.exchange for entry in entries} == {"ALXP", "XPAR"}
    assert all(entry.country == "France" for entry in entries)
    assert [call["iDisplayStart"] for call in fake_client.post_calls] == [0, 100]


def test_discover_french_listed_companies_falls_back_to_download_csv_when_aadata_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_page = {
        "iTotalDisplayRecords": 2,
        "aaData": [[], []],
    }
    csv_payload = (
        "Name;ISIN;Symbol;Market;Currency\n"
        '"European Equities"\n'
        '"28 Apr 2026"\n'
        "2CRSI;FR0013341781;AL2SI;Euronext Growth Paris;EUR\n"
        "TotalEnergies;FR0000120271;TTE;Euronext Paris;EUR\n"
    )
    fake_client = _FakeClient(post_payloads=[first_page], csv_payload=csv_payload)
    monkeypatch.setattr(
        "src.repositories.euronext_discovery_repository.httpx.Client",
        lambda **kwargs: fake_client,
    )

    entries = discover_french_listed_companies(page_size=100)

    assert len(entries) == 2
    assert {entry.ticker for entry in entries} == {"AL2SI.PA", "TTE.PA"}
    assert any("/pd_es/data/stocks/download?" in url for url in fake_client.get_calls)


def test_discover_french_listed_companies_raises_on_invalid_response(monkeypatch: pytest.MonkeyPatch) -> None:
    invalid_payload = {"iTotalDisplayRecords": 1}
    fake_client = _FakeClient(post_payloads=[invalid_payload])
    monkeypatch.setattr(
        "src.repositories.euronext_discovery_repository.httpx.Client",
        lambda **kwargs: fake_client,
    )

    with pytest.raises(EuronextResponseError, match="aaData"):
        discover_french_listed_companies()
