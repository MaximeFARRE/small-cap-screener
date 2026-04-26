# Product Roadmap — French Small Cap Screener

Architecture rule: `UI -> Services -> Repositories`.

## Product Goal

Deliver a local desktop workflow for French small-cap screening that is:

* deterministic (same inputs, same ranking output),
* auditable (explicit scoring rules and analyst decisions),
* operational (exportable shortlist for research workflow).

Target universe:

* Euronext Paris
* Euronext Growth
* French listed companies

## Current Status (April 2026)

* Data model and local persistence: delivered.
* KPI computation and V1 multi-factor scoring: delivered.
* Global and sector ranking: delivered.
* Analyst workflow (watchlist, notes, status, exclusions): delivered.
* Screening filters/sorting and CSV/Excel exports: delivered.
* Reliability layer (cache, retry/fallback, offline mode, data quality score): delivered.
* Desktop packaging baseline (PyInstaller): delivered.
* Recruiter-ready documentation and demo assets: in progress.

## Delivered Milestones

### Phase 0 to 3 — Foundation and universe

* Repository standards and strict layered architecture enforced.
* Core models/repositories stabilized on SQLite/SQLAlchemy.
* French small-cap universe ingestion and normalization in place.

### Phase 4 to 6 — Financial data and KPI engine

* Financial ingestion pipeline implemented (fetch, normalize, persist).
* KPI snapshots generated with resilient batch behavior.
* Missing/incomplete data handled without pipeline crash.

### Phase 7 to 9 — Scoring and screening services

* Deterministic scoring V1 with sub-scores: quality, value, growth, risk.
* Global and sector ranking computed from scored snapshots.
* Screening service supports list, filter, sort, and export.

### Phase 10 to 11 — Analyst desktop workflow

* Desktop screener UI connected to service layer.
* Analyst detail panel includes scores, explanation, notes, status, exclusion.
* Screening snapshots and exports support recurring analyst workflow.

### Phase 12 to 13 — Reliability and release readiness

* Provider calls hardened with cache, retry, fallback, and offline mode.
* Data quality score added to highlight low-confidence dossiers.
* CI quality gates aligned (`pytest`, `ruff`, `black --check`) and desktop build configured.

## Next Priorities (Post-V1)

1. Increase market data depth and provider redundancy for stronger coverage.
2. Add benchmark/backtesting views to validate ranking usefulness over time.
3. Add reproducible demo dataset and screenshots for portfolio/recruiting presentation.
4. Prepare lightweight installer/distribution flow for non-technical users.

## Deliberate Non-Goals (V1)

* No cloud deployment.
* No multi-user or access management.
* No real-time streaming or execution.
* No AI-generated investment decisions.
