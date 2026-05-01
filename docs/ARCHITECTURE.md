# Architecture (v2)

This project uses a strict layered architecture with explicit ownership of responsibilities.

## Core Principle

```text
Frontend -> API -> Services -> Repositories -> Database / External Providers
```

Rules:
- no business logic in frontend
- API routers call services only
- repositories own persistence and external IO
- no layer bypass

## Layer Responsibilities

## Frontend Layer (`frontend/src`)

Responsibilities:
- render panels, tables, charts, and forms
- handle user interactions and UI state
- fetch data through typed API hooks

Forbidden:
- KPI/scoring calculations
- direct database access
- provider-specific logic

## API Layer (`api/routers`, `api/schemas`)

Responsibilities:
- expose HTTP endpoints
- validate request and response contracts
- orchestrate service calls

Rules:
- no direct repository access from routers
- no business rule implementation in routers

## Services Layer (`src/services`)

Responsibilities:
- ingestion orchestration
- KPI computation
- scoring and ranking
- screening/filtering/export behavior
- workflow orchestration for refresh/import

Rules:
- no UI dependencies
- no presentation formatting concerns
- reuse existing services before creating new ones

## Repository Layer (`src/repositories`)

Responsibilities:
- SQLAlchemy and SQLite data access
- external data provider integration

Rules:
- no business decisions
- no cross-layer orchestration

## Operational Flows

## Universe import and enrichment

1. API receives import request.
2. `UniverseService` discovers and upserts companies.
3. `UniverseDiscoveryService` enriches companies and updates KPI snapshots.
4. API streams progress events to frontend when using SSE route.
5. Frontend updates global import status and refreshes queries.

## Screener workflow

1. Frontend sends filter payload to API.
2. `ScreeningService` applies filters/sorting and returns rows.
3. Frontend renders panel table and selection state.

## Service Inventory

- `FinancialDataService`: provider orchestration, retry/fallback, normalization entrypoint.
- `NormalizationService`: canonical normalization of raw provider payloads.
- `DataValidationService`: consistency and quality checks.
- `RatioService`: KPI and ratio computation.
- `KpiSnapshotService`: KPI snapshot generation and upsert.
- `ScoringService`: sub-scores, total score, ranking, driver explanations.
- `ScreeningService`: universe filtering, sorting, snapshot workflows, export integration.
- `WatchlistService`: watchlist status, memo and analyst workflow.
- `TickerIngestionService`: ticker/ISIN ingestion from UI/API boundary.
- `TickerResolverService`: exchange suffix resolution and symbol probing.
- `UniverseDiscoveryService`: single/batch refresh and progress-aware enrichment.
- `UniverseService`: universe discovery and investable universe management.
- `CompanyDetailService`: tearsheet-ready aggregate company payload.
- `CompanyChartsService`: chart-friendly transformed series.
- `PeerComparisonService`: peer set and sector median comparisons.
- `BacktestingService`: ranking validation and forward-return analysis.
- `ExportService`: CSV/XLSX exports.

## Provider Abstractions

- `BaseProvider`: provider contract.
- `YFinanceProvider`: Yahoo Finance implementation.
- `ChainedProvider`: ordered fallback provider strategy.
- `NoOpProvider`: safe offline/testing fallback.

## Data and Migrations

- Local SQLite database by default (`data/screener.db`).
- Schema evolution is handled in Python startup routines (no Alembic).
- Maintenance operations (backup, vacuum, reset) are implemented in services.

## Guardrails

- Keep changes small and targeted.
- Avoid logic duplication across services.
- Document assumptions when behavior is ambiguous.
