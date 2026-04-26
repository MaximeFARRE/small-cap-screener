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

* `FinancialDataService`: ingestion, retry/fallback/offline orchestration.
* `NormalizationService`: canonical data normalization.
* `RatioService`: KPI calculations.
* `ScoringService`: sub-scores, total score, ranking, score explanation.
* `ScreeningService`: scored universe listing, filters, sorting, exports, screening snapshots.
* `WatchlistService`: notes/status/exclusion workflow and analyst company detail.

## Guardrails

* Prefer targeted edits over broad rewrites.
* Keep one logical concern per change.
* Avoid duplicate logic across services.
* If behavior is ambiguous, define assumptions explicitly before coding.
