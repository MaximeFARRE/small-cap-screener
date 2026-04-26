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


## Phase 14 — Real ticker ingestion from the app

* Add company manually from a Yahoo Finance ticker inside the desktop app
* Validate ticker format and show clear error messages
* Fetch company profile, price history, market data and financial statements from provider
* Create or update the company in local DB automatically
* Trigger normalization, KPI snapshot, scoring and ranking after ingestion
* Refresh screener table immediately after successful import
* Remove dependency on manual CSV import for normal user workflow

## Phase 15 — Real company financial detail page

* Display current price and market cap
* Display enterprise value when computable
* Display revenue, EBITDA/operating income, net income, free cash flow and net debt
* Display valuation ratios: P/E, P/B, EV/EBITDA, EV/Sales, FCF yield
* Display quality ratios: margins, ROE/ROA/ROIC if available
* Display growth metrics: revenue growth, earnings growth, FCF growth
* Display risk metrics: leverage, liquidity, volatility/data confidence if available
* Show latest financial period used for each metric
* Clearly mark missing or unreliable values

## Phase 16 — Provider coverage and ticker resolution

* Improve Yahoo Finance ticker handling for French stocks
* Add ticker suffix assistance (`.PA`, `.AL`, etc.)
* Add provider response validation before saving data
* Add clear distinction between no data, invalid ticker and temporary provider error
* Add provider health diagnostics in logs
* Prepare provider abstraction for future redundancy

## Phase 17 — Universe discovery without CSV workflow

* Add an in-app way to build or refresh the French small-cap universe
* Start from provider/search sources where possible
* Allow manual ticker addition as fallback
* Store source and refresh date for every company
* Add universe refresh service to update existing companies in batch
* Keep CSV seed only as demo/dev fixture, not as core user flow

## Phase 18 — Full refresh workflow

* Add one-click refresh for selected company
* Add one-click refresh for watchlist
* Add one-click refresh for full universe
* Show progress, success count, failure count and error details
* Ensure batch refresh is resilient company by company
* Preserve existing notes, status, exclusions and snapshots during refresh

## Phase 19 — Data freshness and quality UI

* Display last data refresh date per company
* Display last KPI snapshot date
* Display data quality score in screener and detail panel
* Add warning badges for stale, incomplete or low-quality data
* Add filter for minimum data quality
* Add filter for recently refreshed companies

## Phase 20 — Ratio table and historical fundamentals

* Add a dedicated ratios table in company detail page
* Show latest metrics and historical values over several years when available
* Add revenue, margin, earnings and cash-flow history
* Add debt and balance sheet evolution
* Add CAGR calculations where data quality allows it
* Add simple trend indicators without over-engineering

## Phase 21 — Score transparency and scoring configuration

* Display how total score is built from quality, value, growth and risk
* Show strongest positive and negative score contributors
* Add score explanation at factor level, not only summary level
* Allow basic scoring weights configuration in a service/config layer
* Keep scoring deterministic and auditable
* Add tests ensuring ranking changes correctly when weights change

## Phase 22 — Analyst memo workflow

* Add structured analyst memo fields:
  * investment thesis
  * risks
  * catalysts
  * valuation notes
  * next action
* Persist memo locally
* Display memo in company detail page
* Allow editing without breaking watchlist notes
* Add export-ready memo format

## Phase 23 — Advanced watchlist workflow

* Add watchlist views by status: watching, review, conviction, rejected
* Add filters for watchlist only / non-watchlist only
* Add filter for excluded companies
* Add next review date
* Add simple analyst action queue
* Preserve all workflow data across refreshes

## Phase 24 — Screening snapshots V2

* Add UI action to create a screening snapshot
* List previous screening snapshots
* Open and inspect a saved snapshot
* Compare current ranking vs previous snapshot
* Show rank changes and score changes
* Keep snapshot format stable and readable

## Phase 25 — Export polish

* Improve CSV and Excel formatting
* Add export for current screener view
* Add export for watchlist only
* Add export for company memo
* Add export for screening snapshot
* Add metadata sheet in Excel exports with date, filters and scoring version

## Phase 26 — Charts and visual analysis

* Add price history chart
* Add revenue and EBITDA chart
* Add margin evolution chart
* Add score breakdown visual
* Add simple ranking distribution chart
* Keep charts lightweight and desktop-friendly

## Phase 27 — Benchmark and relative analysis

* Add sector peer comparison
* Compare valuation ratios against sector median
* Compare quality/growth/risk against sector median
* Add relative rank within sector
* Add simple peer table in company detail page
* Avoid advanced backtesting until data coverage is strong enough

## Phase 28 — Backtesting and ranking validation

* Save historical score snapshots over time
* Track forward performance after ranking date
* Compare top-ranked bucket vs lower-ranked bucket
* Add basic benchmark comparison if data is available
* Add performance summary by score factor
* Clearly mark limitations and data bias

## Phase 29 — Provider redundancy

* Add a second provider interface if a reliable free/affordable source is selected
* Implement fallback provider logic
* Compare conflicting provider values explicitly
* Store provider source per data point or snapshot when useful
* Add tests for provider fallback behavior

## Phase 30 — Error handling and user feedback polish

* Replace technical errors in UI with clear user messages
* Add detailed logs for developers
* Add retry feedback in UI during refresh
* Add provider unavailable state
* Add invalid ticker state
* Add partial success state for batch refresh

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
