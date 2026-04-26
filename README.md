# Small Cap Screener

Local-first desktop application to screen French listed small-cap companies with a deterministic and auditable workflow.

## Problem Solved

Analysts often lose time between scattered data pulls, ad-hoc spreadsheets, and non-reproducible scoring logic.
This project provides one coherent workflow: ingest data, compute KPIs, score companies, rank the universe, and keep analyst decisions traceable.

## Why This Project Matters

* Reduces manual screening overhead on French small/mid-cap coverage.
* Makes ranking decisions reproducible with explicit scoring rules.
* Keeps analyst judgment in the loop (watchlist notes, status, exclusions).
* Produces operational outputs directly usable in research workflow (CSV/Excel exports, saved snapshots).

## What Is Implemented

* KPI pipeline (valuation, quality, growth, risk metrics)
* Deterministic scoring V1 (quality/value/growth/risk + total score)
* Global and sector ranking on the scored universe
* Analyst workflow (watchlist, notes, status, exclusions)
* Historical fundamentals in company detail (multi-year table, CAGR, trend flags)
* Screening filters/sorting + CSV and Excel exports
* Screening snapshots to freeze filtered/ranked results at a given date
* Reliability features (cache, retry/fallback, offline mode, data quality score)
* Desktop UI (PySide6) connected to service layer only

## Analyst Workflow (End-to-End Demo)

1. Refresh company financial data and KPI snapshots.
2. Apply scoring service to compute sub-scores and total score.
3. Rank the universe globally and by sector.
4. Filter screener output and review company analyst detail.
5. Update watchlist notes/status/exclusion, then export or save a screening snapshot.

## Architecture

```
UI -> Services -> Repositories
```

* UI: display and user input only.
* Services: business logic and orchestration.
* Repositories: database access and external provider calls.

Detailed architecture: `docs/ARCHITECTURE.md`.

## Stack

* Python 3.11+
* PySide6 (desktop UI)
* SQLite + SQLAlchemy
* pandas / numpy
* pytest / ruff / black / pre-commit
* PyInstaller (desktop packaging)

Detailed stack: `STACK.md`.

## Getting Started (Windows)

```bash
git clone <repo-url>
cd small-cap-screener
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pre-commit install
```

Run app:

```bash
python -m src.ui.app
```

## Local Demo Dataset

The repository includes a stable, synthetic (but realistic) French small-cap demo dataset:

* fixed universe seed (`data/demo/seed_universe_fr_small_caps.csv`)
* KPI snapshots with deterministic scoring and ranking
* watchlist analyst notes/status
* one excluded company to demonstrate analyst filtering behavior

Build/reset the local demo data:

```bash
python -m src.demo_dataset
```

Then launch the app:

```bash
python -m src.ui.app
```

## Desktop Packaging

```bash
pip install -r requirements-dev.txt
python -m PyInstaller --clean --noconfirm small_cap_screener.spec
```

Build output:

```text
dist/small-cap-screener/small-cap-screener.exe
```

## Releases

Automated releases use `python-semantic-release` on `main` with Conventional Commits.
Release process: `docs/RELEASE.md`.

## Documentation

* Roadmap: `docs/ROADMAP.md`
* Architecture: `docs/ARCHITECTURE.md`
* Known limitations: `docs/KNOWN_LIMITATIONS.md`
