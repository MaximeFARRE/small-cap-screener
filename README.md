<div align="center">

# Small Cap Screener

**Version 2.4.0 — local-first research terminal for French small & mid caps**

[![Version](https://img.shields.io/badge/Version-2.4.0-blue?style=flat-square)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-Strict-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![SQLite](https://img.shields.io/badge/DB-SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy-D71F00?style=flat-square)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## What This Project Is

Small Cap Screener is a local research platform for buy-side workflows on French listed small and mid-cap equities (Euronext Paris, Growth, Access).

The app centralizes the workflow:

`ingest → normalize → compute KPI → score → rank → annotate → export`

Everything runs locally, with no cloud dependency and no mandatory external SaaS account.

---

## Architecture

```
Frontend (React + TypeScript + Vite)
            ↓
API layer (FastAPI + Pydantic)
            ↓
Services (business logic)
            ↓
Repositories (DB / API access)
            ↓
SQLite
```

Core rules:
- no business logic in the frontend
- API routers call services only
- repositories own all persistence and provider I/O

Reference: [STACK.md](STACK.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Main Features

### Universe & Enrichment
- Euronext France universe discovery and import
- Ticker and ISIN ingestion
- Yahoo Finance enrichment with fallback logic
- Data freshness and quality indicators per company

### Scoring & Screening
- 8-bloc deterministic fundamental scoring engine (see below)
- Global and sector ranking
- Filterable and sortable screener with snapshot export
- Company profile classification

### Analyst Workflow
- Tearsheet with KPIs, score breakdown, historical financials, and price chart
- Peer comparison and signal panels
- Watchlist with memo and status management

### Export
- CSV and Excel exports from filtered or snapshot views

---

## Scoring Engine

The scoring engine produces a **total score (0–100)** computed from **8 internal blocs**, each covering a distinct analytical dimension. The blocs aggregate into 4 public sub-scores that are weighted into the total.

### 8 blocs → 4 sub-scores

| Bloc | Weight | Metrics | Sub-score |
|---|---|---|---|
| `business_quality` | 15% | gross_margin, roic, roce, asset_turnover | **Quality** (35%) |
| `profitability` | 14% | gross_profitability, roa, roic, ebit_margin | **Quality** (35%) |
| `cash_flow_quality` | 12% | cfo_to_net_income, cfo_to_ebit, fcf_margin, cfo_margin, cfo_streak_negative | **Quality** (35%) |
| `valuation` | 10% | ev_ebit, ev_fcf, ev_sales, pb_ratio | **Value** (30%) |
| `growth_trajectory` | 12% | gross_profit_growth, revenue_growth, revenue_cagr_3y, ebitda_growth | **Growth** (20%) |
| `capital_allocation` | 10% | ronic, capex_to_revenue, shares_growth | **Growth** (20%) |
| `balance_sheet_strength` | 14% | net_debt_to_ebitda, interest_coverage, current_ratio, debt_to_equity | **Risk** (15%) |
| `risk_inverse` | 13% | altman_z_proxy, beta, accrual_ratio | **Risk** (15%) |

Each metric is scored 0–100 by linear interpolation between a `good` and `bad` threshold defined in `scoring_config.py`. Missing metrics score 0 and reduce the effective weight of their bloc.

### Pipeline

```
compute 8 blocs
    → bridle valuation (cap at 50 if quality or risk avg < 30)
    → apply reinvestment CFO relief (lift cash_flow_quality to floor 35 if reinvestment phase)
    → aggregate into 4 sub-scores
    → weighted total
    → anti-compensation penalty (min bloc score < 20 → penalty applied)
    → context adjustment (mutually exclusive, −11 to +6)
    → red flag cap
    → clamp [0, 100]
```

### Context adjustments (mutually exclusive)

| Profile | Adjustment |
|---|---|
| distressed | −11 pts |
| value_trap | −10 pts |
| turnaround (unconfirmed) | −2 pts |
| turnaround (confirmed) | +2 pts |
| cyclical | +5 pts |
| reinvestment_phase | +6 pts |

### Red flag caps

| Condition | Cap |
|---|---|
| Distressed (high debt + low coverage) | 35 |
| Value trap (shrinking revenue + rich valuation) | 45 |
| Dangerous debt (net debt / EBITDA > 4) | 45 |
| Unconfirmed turnaround (negative EBIT, weak growth) | 65 |

### Company profile labels

Each snapshot is classified into one mutually exclusive profile (stored as `profile_label`):

`compounder` · `reinvestment_phase` · `cyclical` · `turnaround` · `value_trap` · `distressed` · `low_visibility` · `standard`

The cascade follows the order above: distress is checked first, compounder last before standard.

---

## Tech Stack

### Backend
- Python 3.11+
- FastAPI, Uvicorn, Pydantic
- SQLAlchemy, SQLite
- pandas, numpy, yfinance

### Frontend
- React 18 + Vite
- TypeScript (strict)
- React Router
- TanStack Query
- Tailwind CSS + shadcn/ui

---

## Getting Started (Development)

### 1) Backend setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2) Frontend setup

```bash
cd frontend
npm install
cd ..
```

### 3) Run backend API

```bash
.venv\Scripts\activate
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### 4) Run frontend

```bash
cd frontend
npm run dev
```

Frontend runs on the Vite dev server and proxies API calls to `/api`.

---

## Quality Checks

Backend:
```bash
ruff check .
ruff format --check .
pytest
```

Frontend:
```bash
cd frontend
npm run lint
npm run build
```

---

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- [docs/RELEASE.md](docs/RELEASE.md)
- [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md)
- [STACK.md](STACK.md)
- [CHANGELOG.md](CHANGELOG.md)

---

## License

MIT — see [LICENSE](LICENSE)
