# Known Limitations (v2)

This document lists current limitations and explicit non-goals for version 2.

## Data and coverage

- Universe scope is focused on French listed equities (Euronext Paris/Growth/Access).
- Data quality depends on third-party provider consistency and uptime.
- Coverage depth remains below premium institutional vendor datasets.

## Product boundaries

- Local-first single-user workflow only.
- No built-in authentication, roles, or multi-tenant model.
- No cloud sync or centralized collaboration backend.

## Scoring model

- Deterministic scoring is rule-based and configurable, not ML-driven.
- Calibration is practical for shortlist prioritization, not a standalone investment decision engine.

## Frontend and testing

- Frontend quality gates include lint/build, but full E2E browser automation is limited.
- UI behavior across very large universes still needs additional stress testing.

## Operations and deployment

- Primary workflow is local development/runtime.
- Production-grade deployment hardening (monitoring, observability, rollback playbooks) is limited.

## Deliberate non-goals for v2

- no execution or order management
- no real-time streaming market feed
- no AI-generated buy/sell recommendation

For future priorities, see [ROADMAP.md](./ROADMAP.md).
