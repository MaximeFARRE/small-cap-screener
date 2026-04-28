from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterable
from urllib.parse import quote

import httpx

from src.repositories.seed_universe_repository import SeedUniverseEntry

DEFAULT_PARIS_MICS: tuple[str, ...] = ("XPAR", "ALXP", "XMLI")
DEFAULT_COUNTRY: str = "France"
DEFAULT_SECTOR: str = "Unknown"
DEFAULT_PAGE_SIZE: int = 100
DEFAULT_TIMEOUT_SECONDS: float = 30.0

_EURONEXT_BASE_URL: str = "https://live.euronext.com"
_EURONEXT_DATA_PATH: str = "/en/pd_es/data/stocks"
_EURONEXT_DOWNLOAD_PATH: str = "/pd_es/data/stocks/download"
_DISPLAY_DATAPOINTS: str = "dp_stocks"
_DISPLAY_FILTERS: str = "df_stocks2"

_MIC_TO_YFINANCE_SUFFIX: dict[str, str] = {
    "XPAR": ".PA",
    "ALXP": ".PA",
    "XMLI": ".PA",
}

_MARKET_NAME_TO_MIC: dict[str, str] = {
    "euronext paris": "XPAR",
    "euronext growth paris": "ALXP",
    "euronext access paris": "XMLI",
}

_NAME_FROM_LINK_REGEX = re.compile(r'data-order="([^"]+)"|data-order=\'([^\']+)\'')
_TEXT_IN_TAG_REGEX = re.compile(r">([^<]+)<")
_TITLE_ATTR_REGEX = re.compile(r'title="([^"]+)"|title=\'([^\']+)\'')
_CURRENCY_REGEX = re.compile(r"\b[A-Z]{3}\b")


class EuronextDiscoveryError(Exception):
    """Raised when discovery from Euronext fails."""


class EuronextResponseError(EuronextDiscoveryError):
    """Raised when Euronext returns an invalid response payload."""


def discover_french_listed_companies(
    *,
    mics: tuple[str, ...] = DEFAULT_PARIS_MICS,
    page_size: int = DEFAULT_PAGE_SIZE,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[SeedUniverseEntry]:
    if page_size <= 0:
        raise ValueError("page_size must be > 0")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be > 0")
    if not mics:
        raise ValueError("mics cannot be empty")

    encoded_mics = quote(",".join(mics))
    gateway_url = (
        f"{_EURONEXT_BASE_URL}{_EURONEXT_DATA_PATH}"
        f"?mics={encoded_mics}&display_datapoints={_DISPLAY_DATAPOINTS}&display_filters={_DISPLAY_FILTERS}"
    )
    download_url = (
        f"{_EURONEXT_BASE_URL}{_EURONEXT_DOWNLOAD_PATH}"
        f"?mics={encoded_mics}&display_datapoints={_DISPLAY_DATAPOINTS}&display_filters={_DISPLAY_FILTERS}"
    )

    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        first_payload = _fetch_page_payload(client, gateway_url, start=0, page_size=page_size)
        total_records = _extract_total_records(first_payload)
        first_page_rows = _extract_aa_data_rows(first_payload)

        if total_records > 0 and _rows_are_empty(first_page_rows):
            # Some Euronext responses return empty aaData rows unless the page is fully hydrated.
            # In that case fallback to the official downloadable table endpoint.
            return _discover_from_download_csv(client, download_url)

        entries = _parse_rows_to_entries(first_page_rows)
        for start in range(page_size, total_records, page_size):
            payload = _fetch_page_payload(client, gateway_url, start=start, page_size=page_size)
            rows = _extract_aa_data_rows(payload)
            entries.extend(_parse_rows_to_entries(rows))

    return _deduplicate_entries(entries)


def _fetch_page_payload(client: httpx.Client, url: str, *, start: int, page_size: int) -> dict:
    payload = {
        "draw": 3,
        "columns[0][data]": 0,
        "columns[0][name]": "",
        "search[value]": "",
        "search[regex]": "false",
        "args[initialLetter]": "",
        "iDisplayLength": page_size,
        "iDisplayStart": start,
        "sSortDir_0": "asc",
        "sSortField": "name",
    }
    try:
        response = client.post(url, data=payload)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise EuronextDiscoveryError(f"Euronext request failed: {exc}") from exc
    except ValueError as exc:
        raise EuronextResponseError("Euronext returned a non-JSON response") from exc

    if not isinstance(data, dict):
        raise EuronextResponseError("Euronext response is not a JSON object")
    return data


def _extract_total_records(payload: dict) -> int:
    value = payload.get("iTotalDisplayRecords")
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError) as exc:
        raise EuronextResponseError("Invalid iTotalDisplayRecords in Euronext response") from exc


def _extract_aa_data_rows(payload: dict) -> list[list]:
    rows = payload.get("aaData")
    if rows is None:
        raise EuronextResponseError("Missing aaData in Euronext response")
    if not isinstance(rows, list):
        raise EuronextResponseError("aaData is not a list in Euronext response")
    return [row for row in rows if isinstance(row, list)]


def _rows_are_empty(rows: Iterable[list]) -> bool:
    for row in rows:
        if any(str(cell).strip() for cell in row):
            return False
    return True


def _parse_rows_to_entries(rows: Iterable[list]) -> list[SeedUniverseEntry]:
    entries: list[SeedUniverseEntry] = []
    for row in rows:
        entry = _parse_row_to_entry(row)
        if entry is not None:
            entries.append(entry)
    return entries


def _parse_row_to_entry(row: list) -> SeedUniverseEntry | None:
    if len(row) < 6:
        return None

    raw_name_link = str(row[1]).strip()
    isin = str(row[2]).strip().upper()
    symbol = str(row[3]).strip().upper()
    market_html = str(row[4]).strip()
    currency_html = str(row[5]).strip()

    if not isin or not symbol or not raw_name_link:
        return None

    name = _extract_name(raw_name_link)
    mic, market_label = _extract_market(market_html)
    ticker = _normalize_ticker(symbol, mic=mic, market_label=market_label)
    currency = _extract_currency(currency_html)
    exchange = mic or market_label or "XPAR"

    return SeedUniverseEntry(
        name=name,
        ticker=ticker,
        isin=isin,
        exchange=exchange,
        country=DEFAULT_COUNTRY,
        sector=DEFAULT_SECTOR,
        currency=currency,
    )


def _extract_name(name_link_html: str) -> str:
    match = _NAME_FROM_LINK_REGEX.search(name_link_html)
    if match is None:
        return _extract_text_from_html(name_link_html)
    first = match.group(1)
    second = match.group(2)
    if first is not None and first.strip():
        return first.strip()
    if second is not None and second.strip():
        return second.strip()
    return _extract_text_from_html(name_link_html)


def _extract_market(market_html: str) -> tuple[str | None, str | None]:
    market_code = _extract_text_from_html(market_html).upper() or None
    title_match = _TITLE_ATTR_REGEX.search(market_html)
    market_label: str | None = None
    if title_match is not None:
        market_label = (title_match.group(1) or title_match.group(2) or "").strip() or None

    if market_code is None and market_label is not None:
        market_code = _market_label_to_mic(market_label)
    return market_code, market_label


def _extract_currency(currency_html: str) -> str:
    match = _CURRENCY_REGEX.search(currency_html)
    if match is None:
        return "EUR"
    return match.group(0).upper()


def _extract_text_from_html(html_fragment: str) -> str:
    matches = _TEXT_IN_TAG_REGEX.findall(html_fragment)
    if not matches:
        return html_fragment.strip()
    return " ".join(piece.strip() for piece in matches if piece.strip()).strip()


def _normalize_ticker(symbol: str, *, mic: str | None, market_label: str | None) -> str:
    if "." in symbol:
        return symbol

    suffix: str | None = None
    if mic is not None:
        suffix = _MIC_TO_YFINANCE_SUFFIX.get(mic.upper())
    if suffix is None and market_label is not None:
        mapped_mic = _market_label_to_mic(market_label)
        if mapped_mic is not None:
            suffix = _MIC_TO_YFINANCE_SUFFIX.get(mapped_mic)
    return f"{symbol}{suffix}" if suffix is not None else symbol


def _market_label_to_mic(label: str) -> str | None:
    return _MARKET_NAME_TO_MIC.get(label.strip().lower())


def _deduplicate_entries(entries: list[SeedUniverseEntry]) -> list[SeedUniverseEntry]:
    by_identity: dict[tuple[str, str], SeedUniverseEntry] = {}
    for entry in entries:
        key = (entry.isin.upper(), entry.ticker.upper())
        by_identity[key] = entry
    return list(by_identity.values())


def _discover_from_download_csv(client: httpx.Client, download_url: str) -> list[SeedUniverseEntry]:
    try:
        response = client.get(download_url)
        response.raise_for_status()
        content = response.text
    except httpx.HTTPError as exc:
        raise EuronextDiscoveryError(f"Euronext CSV download failed: {exc}") from exc

    reader = csv.DictReader(io.StringIO(content), delimiter=";")
    entries: list[SeedUniverseEntry] = []
    for row in reader:
        if row is None:
            continue
        isin = (row.get("ISIN") or "").strip().upper()
        symbol = (row.get("Symbol") or "").strip().upper()
        name = (row.get("Name") or "").strip()
        market_label = (row.get("Market") or "").strip()
        currency = (row.get("Currency") or "").strip().upper() or "EUR"

        if not isin or not symbol or not name:
            continue

        mic = _market_label_to_mic(market_label)
        ticker = _normalize_ticker(symbol, mic=mic, market_label=market_label)
        exchange = mic or market_label or "XPAR"

        entries.append(
            SeedUniverseEntry(
                name=name,
                ticker=ticker,
                isin=isin,
                exchange=exchange,
                country=DEFAULT_COUNTRY,
                sector=DEFAULT_SECTOR,
                currency=currency,
            )
        )
    return _deduplicate_entries(entries)
