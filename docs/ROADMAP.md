# Roadmap

Desktop financial screener for French small-cap companies.
Architecture: UI → Services → Repositories.

---

## Phase 1 — Core Data Layer (current)

- [x] Project scaffold and configuration
- [x] Data models: Company, FinancialStatement, PriceHistory, ScreeningSnapshot
- [x] Database initialization and session management (`database.py`)
- [x] Company repository (CRUD)
- [x] Financial statement repository (CRUD)
- [x] Unit tests for repositories

---

## Phase 2 — Business Logic

- [x] Financial ratio computation service (P/E, P/B, EV/EBITDA, etc.)
- [x] Multi-factor scoring service
- [x] Screening and filtering service
- [x] Unit tests for services

---

## Phase 3 — External Data

- [ ] HTTP client for financial data API (httpx, via repository layer)
- [ ] Data ingestion pipeline (fetch → parse → store)
- [ ] Error handling and retry logic for API calls

---

## Phase 4 — UI

- [ ] Main window scaffold (PySide6)
- [ ] Company list / screener table view
- [ ] Company detail panel
- [ ] Screening filter controls
- [ ] Export to CSV and Excel

---

## Phase 5 — Polish

- [ ] Full test coverage (repositories, services)
- [ ] Packaging / distribution (PyInstaller or similar)
- [ ] User documentation

---

## Out of Scope

- Web backend or cloud deployment
- Multi-user support
- Real-time data streaming
- AI/ML scoring (may be revisited later as optional)
