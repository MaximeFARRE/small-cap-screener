# V1 Roadmap — French Small Cap Screener

Architecture rule:
`UI → Services → Repositories`

Goal:
Build a professional desktop screener for French listed small-cap companies with reliable financial data, KPI calculation, ranking logic, and analyst workflow.

Target universe:

* Euronext Paris
* Euronext Growth
* French listed companies only

Out of scope V1:

* Private companies
* Cloud deployment
* Multi-user
* Real-time streaming
* AI-generated investment decisions

---

## Phase 0 — Repo alignment

* Verify current architecture
* Update README, ROADMAP, ARCHITECTURE, KNOWN_LIMITATIONS
* Confirm strict layer ownership
* Prepare clean development branch

## Phase 1 — Data models and database

* Finalize models for companies, statements, prices, KPI snapshots
* Stabilize SQLite structure
* Validate repositories and CRUD flows

## Phase 2 — External providers

* Create provider layer for yfinance + seed universe source
* Centralize API calls, retries, timeout, parsing
* Define provider contracts and fallback logic

## Phase 3 — Small-cap universe

* Build seed universe of French listed companies
* Import and deduplicate tickers / ISIN
* Apply market cap and liquidity filters

## Phase 4 — Financial ingestion

* Build fetch → validate → normalize → store pipeline
* Create FinancialDataService
* Add logs and failure handling

## Phase 5 — Data normalization

* Standardize identifiers, currencies, units, fiscal periods
* Centralize normalization logic
* Guarantee one clean internal format

## Phase 6 — KPI engine

* Compute valuation, quality, growth, debt, liquidity KPIs
* Keep RatioService as single source of truth
* Handle missing and invalid values safely

## Phase 7 — Scoring engine

* Build Quality / Value / Growth / Risk scoring
* Add deterministic ranking model
* Generate final ranked universe

## Phase 8 — Screening service

* Connect KPI snapshots + filters + ranking
* Build top picks and filtered universe queries
* Prepare clean service API for UI

## Phase 9 — Desktop UI

* Main screener table
* Company detail page
* Filters panel
* Score visualization
* Data freshness display

## Phase 10 — Analyst workflow

* Watchlist
* Personal notes
* Exclusions
* CSV / Excel export
* Screening snapshots

## Phase 11 — Reliability

* Cache strategy
* Retry + fallback handling
* Offline mode
* Data quality score
* Clean logs

## Phase 12 — Final delivery

* Full tests + linting
* Packaging (desktop executable)
* Recruiter-ready GitHub presentation
* Demo dataset + screenshots
* Final documentation
