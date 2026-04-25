# Known Limitations

This file documents the current limitations of the project.

The goal is to be transparent about what is unfinished, simplified, or intentionally excluded.

---

## Current Limitations

### Data ingestion

- Financial data ingestion is not fully standardized yet.
- Provider fallback behavior still needs hardening.
- Historical completeness checks are partial.

### KPI and scoring

- KPI coverage is not complete for all target ratios.
- Scoring weights and ranking calibration are still evolving.
- Missing-value handling is not finalized for every metric.

### User interface

- The desktop UI is still in an early stage.
- Advanced filtering and score visualization are incomplete.
- Data freshness indicators are not fully implemented.

### Reliability

- Cache strategy is not finalized.
- Offline mode is not implemented.
- Data quality scoring is still missing.

### Testing

- End-to-end test coverage is incomplete.
- Edge-case and failure-path tests still need to be expanded.

---

## Deliberate Non-Goals (V1)

- No multi-user support.
- No cloud deployment.
- No real-time streaming.
- No AI-generated investment decisions.

---

## Future Improvements

See [ROADMAP.md](./ROADMAP.md) for planned improvements and future work.
