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
* Analyst memo workflow (thesis, risks, catalysts, valuation notes, next action): delivered.
* Historical fundamentals and multi-year CAGR table: delivered.
* Scoring transparency and weight configuration: delivered.
* Real ticker and ISIN ingestion from the app (no CSV required): delivered.
* Screening filters/sorting and CSV/Excel exports: delivered.
* Screening snapshots V2 with comparison: delivered.
* Charts and visual analysis: delivered.
* Sector peer comparison: delivered.
* Backtesting and ranking validation service: delivered.
* Provider redundancy layer (`ChainedProvider`, `NoOpProvider`, `YFinanceProvider`): delivered.
* Error feedback polish (clean user-facing messages in French): delivered.
* Reliability layer (retry/fallback, offline mode, data quality score): delivered.
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

* Provider calls hardened with retry, fallback, and offline mode.
* Data quality score added to highlight low-confidence dossiers.
* CI quality gates aligned (`pytest`, `ruff check`, `ruff format --check`) and desktop build configured.


### Phase 14 to 19 — Real ingestion, refresh workflow, and data freshness UI

* Real ticker and ISIN ingestion from the desktop app (no CSV required).
* Ticker format validation and suffix resolution (`.PA`, `.AL`, etc.).
* Company profile, price history, market data, and financial statements fetched from provider.
* One-click refresh for single company, watchlist, or full universe.
* Progress feedback with success count, failure count, and error details.
* Data freshness and quality score visible in screener and detail panel.
* Warning indicators for stale or low-confidence data.

### Phase 20 to 22 — Historical fundamentals, scoring transparency, and analyst memo

* Historical financials multi-year table with CAGR and trend indicators.
* Score transparency: weighted sub-score decomposition, positive/negative drivers.
* Sub-score weight configuration in `src/services/scoring_config.py` (deterministic and auditable).
* Structured analyst memo: thesis, risks, catalysts, valuation notes, next action.

### Phase 23 to 25 — Advanced watchlist and export

* Advanced watchlist workflow with status views: watching, review, conviction, rejected.
* Screening snapshots V2: create, list, inspect, and compare vs current ranking.
* Export polish: CSV/Excel with metadata sheet, watchlist export, snapshot export.

### Phase 26 to 28 — Charts, peer comparison, and backtesting

* Price history, revenue/EBITDA, margin evolution, and score breakdown charts.
* Sector peer comparison: valuation, quality/growth/risk ratios vs sector median.
* Backtesting and ranking validation: forward returns by score bucket, hit rate, top-vs-bottom spread.

### Phase 29 — Provider redundancy

* `BaseProvider` abstract interface for all financial data sources.
* `YFinanceProvider`: Yahoo Finance implementation.
* `ChainedProvider`: ordered fallback across multiple providers; non-ProviderError exceptions propagate.
* `NoOpProvider`: safe stub for testing and offline scenarios.

### Phase 30 — Error handling and user feedback polish

* `error_formatter` UI helper: clean French-language messages replacing raw provider exceptions.
* Error kind propagation (`not_found`, `provider_error`, `data_inconsistent`) from provider to UI.
* Batch refresh summary with success/failure counts and first failed tickers.
* `error_kind` field carried through ingestion and refresh result dataclasses.

## Phase 31 — Settings and configuration

* Add basic settings page
* Configure cache TTL
* Configure offline mode
* Configure default filters and sort
* Configure scoring weights if Phase 21 is implemented
* Persist settings locally

## Phase 32 — Database migrations and data maintenance

* Add explicit migration strategy if schema continues evolving
* Add DB backup command or UI action
* Add reset demo data command
* Add vacuum/cleanup maintenance command if useful
* Document DB location and recovery process

## Phase 33 — Performance and scalability

* Test with a larger universe size
* Optimize slow screens and refresh operations
* Avoid blocking UI during long refreshes
* Add background worker pattern for provider calls if needed
* Keep service logic testable outside UI

## Phase 34 — UI polish and usability

* Improve layout and spacing
* Improve table formatting for numbers, percentages and missing values
* Add loading states
* Add empty states with useful actions
* Add consistent badges for status, exclusion and data quality
* Make the app feel like an analyst tool, not a raw dev UI

## Phase 35 — Demo mode and screenshots

* Finalize stable demo dataset
* Add demo launch instructions
* Capture screenshots:
  * main screener
  * add ticker workflow
  * company detail page
  * watchlist workflow
  * export/snapshot workflow
* Add screenshots to README
* Keep screenshots updated with final UI

## Phase 36 — Packaging and installer polish

* Confirm PyInstaller build works from clean environment
* Add versioned build output
* Add icon if available
* Add installer or zipped executable distribution
* Document Windows build process clearly
* Add smoke test checklist after build

## Phase 37 — Final test hardening

* Expand tests on critical user workflows
* Add integration test for ticker ingestion pipeline
* Add integration test for refresh → KPI → score → UI-ready output
* Add regression tests for watchlist/exclusion persistence
* Keep full suite passing with `pytest`, `ruff`, `black --check`

## Phase 38 — Final documentation

* Finalize README for recruiter/investor reader
* Finalize architecture documentation
* Finalize development guide
* Finalize known limitations
* Add “How to demo in 5 minutes”
* Add “What I would improve next” section

## Phase 39 — Recruiter-ready GitHub release

* Clean repository structure
* Remove obsolete files or clearly mark dev-only assets
* Ensure branch/main history is clean enough
* Add release notes for V1
* Add screenshots and demo instructions
* Make the project understandable in under 2 minutes

## Phase 40 — Final V1 acceptance checklist

* User can add a ticker from the app without CSV
* App fetches real provider data
* App computes ratios, KPI, scores and ranking
* App displays useful financial detail page
* App supports watchlist, notes, status and exclusions
* App exports filtered/triaged results
* App can refresh selected company, watchlist or universe
* App handles missing data and provider errors cleanly
* App works offline with local data
* App can be packaged as desktop executable
* README demonstrates the product clearly
* Project is credible for buy-side / AM / PE recruiters
