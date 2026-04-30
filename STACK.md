# STACK.md

## Overview

Buy-side small-cap analysis terminal.

Architecture:
```
Frontend (React) → API layer (FastAPI) → Services → Repositories → SQLite
```

Principles:

- Local-first (no cloud, no multi-user, no auth)
- Simple, modular, maintainable
- No business logic outside the Python services layer
- Compatible with AI-assisted coding

---

## Backend — Python (unchanged from v1)

* Python 3.11+
* pandas, numpy

Rules:

* Services = all business logic
* Repositories = all DB/API access
* Never add logic in the API layer

---

## API Layer — FastAPI

* FastAPI >= 0.111
* Uvicorn (ASGI server)
* Pydantic >= 2.7 (request/response schemas)
* pydantic-settings (env var loading)
* sse-starlette (Server-Sent Events for data refresh progress)

Rules:

* Routers call services only — no direct repository access
* All responses are Pydantic models — no raw ORM serialization
* One router per service domain (screening, companies, watchlist, signals)
* CORS restricted to `FRONTEND_ORIGIN` env var

---

## Frontend — React

* React 18 + Vite
* TypeScript (strict mode, `noUncheckedIndexedAccess`)
* React Router v7
* TanStack Query v5 (server state, caching)

Rules:

* No business logic in frontend — all calculations stay in Python
* Data fetching only in top-level panel components via hooks
* Never use `any` type — derive types from API schemas

---

## UI / Design System

* Tailwind CSS v4 (utility-first, terminal dark palette)
* shadcn/ui (component library, Nova preset)
* Lucide React (icons)
* Terminal dark palette (defined in `src/index.css` and `src/lib/constants.ts`):
  - BG_BASE `#0a0a0f`, BG_PANEL `#0f0f1a`, BG_ELEVATED `#161625`
  - BORDER `#1e1e35`
  - TEXT_PRIMARY `#e2e8f0`, TEXT_MUTED `#64748b`
  - ACCENT `#3b82f6`, POSITIVE `#22c55e`, NEGATIVE `#ef4444`, WARNING `#f59e0b`

Rules:

* Terminal is always in dark mode (`dark` class on `<html>`)
* No light mode support

---

## Charts

* TradingView Lightweight Charts (price history, time-series)
* Recharts (bar/grouped charts for financials)

---

## Panel System

* `react-resizable-panels` (resizable split panes)
* Panel types registered in `frontend/src/panels/registry.ts`
* Inter-panel communication via `WorkspaceContext` (`activeTicker` only)
* Layout persisted to `localStorage`

Rules:

* To add a new panel: create the component + add one entry to `registry.ts`
* No direct props or events between panels — context only

---

## Data

* SQLite
* SQLAlchemy (ORM, repositories layer)

Rules:

* All DB access via repositories
* No raw SQL outside repositories

---

## External Data

* yfinance (primary data provider)
* httpx (HTTP client)

Rules:

* API calls only in repositories

---

## Testing

* pytest (Python)
* No frontend test framework yet (Phase 7+)

---

## Code Quality

* ruff (Python linting and formatting)
* pre-commit (automation)
* TypeScript strict mode (type safety)
* ESLint (frontend linting)

---

## Config

* python-dotenv
* pyyaml
* pydantic-settings (API layer)

---

## Export

* pandas (CSV)
* xlsxwriter (Excel)

---

## Not Included

* No auth or login
* No multi-user
* No cloud deployment
* No AI features (yet)
* No PySide6 (replaced by React)
