# Product Roadmap

Architecture rule: `frontend -> api -> services -> repositories`.

## Version 2.0.0 (current baseline)

Delivered:
- React + Vite frontend workspace with Screener, Tearsheet, Signals, Watchlist panels
- FastAPI API layer with typed request/response models
- Deterministic KPI/scoring/ranking service pipeline
- Universe import and enrichment workflows
- Snapshot, watchlist, memo and export workflows

## v2.x priorities

## 1) Product quality and UX

- improve table performance and consistency on large universes
- extend status/progress feedback for long-running operations
- polish filtering, sorting and keyboard navigation behavior

## 2) Reliability and observability

- stronger error telemetry and categorized failure reporting
- refresh retry policies and timeout hardening
- richer diagnostics for provider fallback decisions

## 3) Data workflows

- incremental refresh strategies by freshness windows
- better snapshot comparison and rank-delta narratives
- improved export schemas for downstream analyst usage

## 4) Testing and CI

- expand backend integration tests around refresh/import flows
- add frontend component and interaction tests
- introduce focused end-to-end smoke checks for critical paths

## v3 direction (exploration)

- configurable deployment profile beyond local-first mode
- richer provider ecosystem and pluggable data sources
- optional AI-assisted research tooling (summaries, memo drafting support)

## Non-goals

- no trade execution engine
- no real-time market data terminal replacement
- no autonomous recommendation engine
