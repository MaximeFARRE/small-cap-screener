# Known Limitations

This document lists current product limitations and deliberate V1 boundaries.

## Current Limitations

### Market and data coverage

* Scope is limited to French listed small caps (Euronext Paris / Growth).
* External data quality depends on third-party provider availability and consistency.
* Coverage depth is lower than institutional premium data terminals.

### Scoring model maturity

* Scoring V1 is deterministic but intentionally simple.
* Weights and thresholds are rule-based and not yet statistically calibrated on long backtests.
* Model is designed for shortlist prioritization, not standalone investment decisioning.

### Product and operations

* Desktop app is local-first and single-user (no shared workspace, no permissions model).
* No cloud sync, no centralized monitoring, no enterprise deployment pipeline.
* Packaging is available via PyInstaller, but installer/signing/distribution workflow is still basic.

### Testing scope

* Unit and service-level coverage is strong; full UI end-to-end automation remains limited.
* Real-world stress testing on very large universes is still to be expanded.

## Deliberate V1 Non-Goals

* No multi-user collaboration layer.
* No cloud backend.
* No real-time market data streaming or execution.
* No AI-generated investment recommendation.

## Improvement Direction

See [ROADMAP.md](./ROADMAP.md) for prioritized post-V1 improvements.
