# Architecture

The project uses a strict layered design to keep financial logic auditable and maintainable.

## Core Principle

```
UI -> Services -> Repositories
```

* UI handles display and user input only.
* Services own business rules, calculations, ranking, and orchestration.
* Repositories own persistence and external provider access.

No layer may bypass this direction.

## Layer Responsibilities

### UI Layer (`src/ui`)

Responsibilities:

* render screener tables, filters, and analyst detail views,
* capture user actions and call service methods,
* display service outputs and empty/error states.

Forbidden in UI:

* KPI/scoring calculations,
* SQL/database access,
* direct provider/API calls.

### Services Layer (`src/services`)

Responsibilities:

* financial ingestion orchestration,
* KPI and scoring calculations,
* screening filters/sorting/export,
* watchlist and analyst workflow behavior.

Rules:

* no UI dependencies,
* no raw SQL,
* reuse existing services before adding new ones.

### Repository Layer (`src/repositories`)

Responsibilities:

* SQLite/SQLAlchemy CRUD and queries,
* provider data fetches and external IO.

Rules:

* no business decisions,
* no formatting/presentation logic.

## Operational Flow (Analyst Workflow)

1. Repositories fetch/store financial and market data.
2. Services normalize and compute KPI snapshots.
3. Services compute scores and ranking.
4. Screening service prepares filtered/sorted universe views and exports.
5. UI renders results and sends analyst actions (notes/status/exclusion) back to services.

## Service Ownership

* `FinancialDataService`: provider fetch orchestration, retry/fallback, offline mode, normalization, validation.
* `NormalizationService`: canonical data normalization (ticker, currency, price history, financial statements).
* `DataValidationService`: cross-field consistency checks before persistence.
* `RatioService`: KPI and financial ratio calculations from normalized data.
* `KpiSnapshotService`: KPI snapshot creation, update, and batch generation per company.
* `ScoringService`: deterministic sub-scores (quality, value, growth, risk), total score, global and sector ranking, score explanation with positive/negative drivers.
* `ScreeningService`: universe listing, filter/sort pipeline, exports (CSV/Excel), screening snapshot management.
* `WatchlistService`: notes, status, exclusion workflow, analyst company detail assembly.
* `TickerIngestionService`: ticker and ISIN ingestion pipeline from the UI (resolve → fetch → KPI snapshot).
* `TickerResolverService`: ticker resolution with exchange suffix probing (`.PA`, `.AL`, etc.).
* `UniverseDiscoveryService`: single-company refresh, batch universe refresh, watchlist refresh with KPI stamp.
* `UniverseService`: investable universe queries and seed data management.
* `CompanyDetailService`: full company detail assembly (profile, ratios, history, score, memo).
* `CompanyChartsService`: chart-ready data for price history, financials, and score breakdown.
* `PeerComparisonService`: sector median computation for peer benchmarking.
* `BacktestingService`: historical ranking validation, bucket forward-return analysis, hit rate.
* `ExportService`: export formatting helpers for CSV and Excel outputs.
* `DemoDatasetService`: synthetic demo dataset generation for development and demo mode.

## Provider Layer (`src/repositories/providers`)

* `BaseProvider`: abstract interface contract for all financial data sources.
* `YFinanceProvider`: Yahoo Finance implementation covering profile, price history, financials, dividends, splits.
* `ChainedProvider`: ordered fallback across multiple providers; re-raises on non-ProviderError exceptions.
* `NoOpProvider`: safe no-op stub for offline testing and development scenarios.

## Guardrails

* Prefer targeted edits over broad rewrites.
* Keep one logical concern per change.
* Avoid duplicate logic across services.
* If behavior is ambiguous, define assumptions explicitly before coding.
