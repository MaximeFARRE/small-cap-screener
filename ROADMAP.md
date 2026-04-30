# ROADMAP.md — Buy-side Small Cap Analysis Terminal

Read `AGENTS.md` and `STACK.md` before any work. This roadmap overrides any
prior technical direction for UI and backend API.

---

## What we are building

A **local-first, multi-panel financial analysis terminal** inspired by Bloomberg
Terminal. Analysts open the app and arrange panels (Screener, Company Tearsheet,
Watchlist, Signals…) in a resizable workspace. The layout is flexible: any
combination of panels can coexist on screen simultaneously.

The Python backend (services, repositories, models) is **not rewritten**. It is
wrapped by a thin FastAPI layer and consumed by a React frontend.

---

## Locked decisions

These decisions are final. Do not re-open them.

| Concern | Decision |
|---|---|
| Python backend | Keep as-is. No rewrite. No structural changes. |
| Backend API | FastAPI. Thin wrapper over existing services. |
| Frontend framework | React 18 + Vite |
| Routing | React Router v6 |
| Styling | Tailwind CSS v3 |
| Component library | shadcn/ui |
| Financial charts | TradingView Lightweight Charts |
| Generic charts | Recharts |
| Panel layout engine | `react-resizable-panels` |
| Server state | TanStack Query (React Query v5) |
| Language | TypeScript strict mode (no `any`, no implicit types) |
| Auth | None. Single-user, local app. |
| Database | SQLite, unchanged. |
| Multi-user | Out of scope permanently. |
| AI features | Out of scope for now. |

---

## Target directory structure

```
small-cap-screener/
│
├── src/                        # Python — UNCHANGED
│   ├── models/
│   ├── repositories/
│   └── services/
│
├── tests/                      # Python tests — UNCHANGED
│
├── api/                        # NEW — FastAPI layer
│   ├── main.py                 # App entry point, CORS, router registration
│   ├── dependencies.py         # Service instantiation (dependency injection)
│   ├── schemas/                # Pydantic response/request schemas
│   │   ├── company.py
│   │   ├── screening.py
│   │   ├── watchlist.py
│   │   ├── scoring.py
│   │   └── signals.py
│   └── routers/                # One router per domain
│       ├── companies.py
│       ├── screening.py
│       ├── watchlist.py
│       ├── scoring.py
│       ├── data_refresh.py
│       └── signals.py
│
├── frontend/                   # NEW — React app
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json           # strict: true
│   ├── tailwind.config.ts
│   ├── package.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       │
│       ├── panels/             # ← CORE CONCEPT: one directory per panel type
│       │   ├── registry.ts     # PanelRegistry: maps panel type → component
│       │   ├── ScreenerPanel/
│       │   ├── TearsheetPanel/
│       │   ├── WatchlistPanel/
│       │   ├── SignalsPanel/
│       │   └── ChartsPanel/
│       │
│       ├── workspace/          # Layout engine — panel arrangement logic
│       │   ├── Workspace.tsx   # Root layout with resizable split panes
│       │   ├── Panel.tsx       # Panel shell (header, type selector, body)
│       │   ├── PanelHeader.tsx
│       │   ├── LayoutPresets.ts  # Predefined layouts (single, split, quad)
│       │   └── useWorkspace.ts   # Hook: open/close/resize panels
│       │
│       ├── components/         # Shared UI components (not panel-specific)
│       │   ├── ScoreBadge.tsx
│       │   ├── MetricCell.tsx
│       │   ├── TrendIndicator.tsx
│       │   ├── DataTable.tsx
│       │   └── LoadingState.tsx
│       │
│       ├── hooks/              # React Query hooks (one per API domain)
│       │   ├── useScreening.ts
│       │   ├── useCompany.ts
│       │   ├── useWatchlist.ts
│       │   ├── useScoring.ts
│       │   └── useSignals.ts
│       │
│       ├── lib/
│       │   ├── api.ts          # Typed API client (fetch wrapper)
│       │   ├── constants.ts    # Thresholds, colors, labels
│       │   └── formatters.ts   # Currency, %, ratio formatting
│       │
│       └── context/
│           └── WorkspaceContext.tsx  # Active company, panel state
│
├── AGENTS.md
├── STACK.md
├── ROADMAP.md
└── .env.example
```

---

## Panel system design

This is the most important architectural concept. Read carefully before building
any panel.

### How panels work

A **panel** is an independent, self-contained React component that:

- Manages its own data fetching via a React Query hook.
- Receives `panelId` and optional initial props via the workspace context.
- Communicates with other panels **only** through `WorkspaceContext` (never via
  direct props or parent state).

### PanelRegistry

`frontend/src/panels/registry.ts` is the **single source of truth** for all
panel types. Adding a new panel type means adding one entry here — nothing else
changes in the layout engine.

```typescript
// panels/registry.ts
export const PANEL_REGISTRY: Record<PanelType, PanelDefinition> = {
  screener:  { label: "Screener",    component: ScreenerPanel  },
  tearsheet: { label: "Tearsheet",   component: TearsheetPanel },
  watchlist: { label: "Watchlist",   component: WatchlistPanel },
  signals:   { label: "Signals",     component: SignalsPanel   },
  charts:    { label: "Charts",      component: ChartsPanel    },
};
```

### WorkspaceContext

Holds the minimal shared state between panels:

```typescript
interface WorkspaceState {
  activeTicker: string | null;          // Set when user clicks a company
  setActiveTicker: (ticker: string) => void;
  layout: PanelLayout;                  // Current panel arrangement
  openPanel: (type: PanelType) => void;
  closePanel: (panelId: string) => void;
}
```

### Inter-panel communication rule

**One pattern only**: a panel writes `activeTicker` to context; other panels
that care re-fetch when `activeTicker` changes. No events, no callbacks, no
Redux, no Zustand.

Example flow:
1. User clicks a row in ScreenerPanel → `setActiveTicker("ALSTOM.PA")`
2. TearsheetPanel watches `activeTicker` → React Query refetches for new ticker
3. ChartsPanel watches `activeTicker` → same

### Layout engine

Use `react-resizable-panels` for split panes. Support three built-in presets
selectable from a toolbar:

| Preset | Layout |
|---|---|
| `single` | One panel, full width |
| `split-h` | Two panels side by side (50/50) |
| `split-v` | Two panels stacked |
| `quad` | 2×2 grid |

Layouts are persisted to `localStorage` between sessions.

---

## API design principles

- **One router per service domain.** Do not create a god router.
- **Endpoints map to service methods, not to DB tables.** The API reflects
  analyst workflows, not the data schema.
- **Pydantic schemas for all responses.** No raw SQLAlchemy model serialization.
  Convert to Pydantic in the router.
- **No business logic in routers.** Routers call services. Services do the work.
- **CORS**: allow `http://localhost:5173` (Vite dev server) in development.

Key endpoints (not exhaustive — derive the rest from the services layer):

```
GET  /api/screening/universe          → ScreeningService.get_universe()
GET  /api/screening/snapshots         → ScreeningService.get_snapshots()
POST /api/screening/snapshot          → ScreeningService.save_snapshot()

GET  /api/companies/{ticker}          → CompanyDetailService.get_detail()
GET  /api/companies/{ticker}/score    → ScoringService.compute_score()
GET  /api/companies/{ticker}/history  → CompanyDetailService.get_financial_history()
GET  /api/companies/{ticker}/peers    → PeerComparisonService.get_peers()
POST /api/companies/refresh           → FinancialDataService.refresh()

GET  /api/watchlist                   → WatchlistService.get_all()
POST /api/watchlist/{ticker}          → WatchlistService.add_company()
DELETE /api/watchlist/{ticker}        → WatchlistService.remove_company()
PATCH /api/watchlist/{ticker}/memo    → WatchlistService.update_memo()

GET  /api/signals                     → derived from ScreeningService snapshots
                                        + KpiSnapshotService movers
```

---

## Phases

---

### Phase 0 — Foundation setup

**Branch:** `chore/pivot-foundation`

**Goal:** Establish the new project structure without touching any existing
Python code. All new directories and config files only.

**Tasks:**

1. Create `api/` directory with empty `__init__.py` files.
2. Create `frontend/` with Vite + React + TypeScript scaffold:
   ```
   pnpm create vite frontend --template react-ts
   ```
3. Configure Tailwind CSS in the frontend project.
4. Install shadcn/ui and initialize it with the dark theme preset.
5. Install `react-resizable-panels`, `@tanstack/react-query`,
   `react-router-dom`, `lightweight-charts`, `recharts`.
6. Create `frontend/src/` directory structure (panels/, workspace/, components/,
   hooks/, lib/, context/) with placeholder `index.ts` files.
7. Add FastAPI and Uvicorn to Python dependencies:
   ```
   fastapi>=0.111
   uvicorn[standard]>=0.30
   pydantic>=2.7
   ```
8. Create `.env.example` entries:
   ```
   API_HOST=127.0.0.1
   API_PORT=8000
   FRONTEND_ORIGIN=http://localhost:5173
   ```
9. Update `STACK.md` to reflect the new stack (FastAPI, React, Vite, Tailwind).
10. Add `api/` and `frontend/` to `.gitignore` exclusions for build artifacts
    (`__pycache__`, `node_modules`, `dist`, `.vite`).

**Definition of done:**
- [ ] `cd frontend && pnpm dev` starts a blank Vite dev server on port 5173.
- [ ] `python -m uvicorn api.main:app --reload` starts without import errors.
- [ ] `STACK.md` updated.
- [ ] No existing Python files modified.

---

### Phase 1 — FastAPI layer

**Branch:** `feat/fastapi-layer`

**Goal:** Expose all necessary Python services as a typed REST API. The
frontend will consume nothing else.

**Rules for this phase:**
- Do not modify any file in `src/`. Read only.
- All service instantiation in `api/dependencies.py` using FastAPI's
  `Depends()` pattern.
- All response bodies defined as Pydantic models in `api/schemas/`.
- Routers are thin: validate input, call service, return schema. No logic.

**Tasks:**

1. `api/dependencies.py`: instantiate all services once using `lru_cache` or
   FastAPI lifespan. Inject via `Depends()`.

2. `api/main.py`: register all routers, configure CORS, set lifespan context.

3. `api/schemas/company.py`:
   - `CompanyRowSchema` (screener row: ticker, name, score, sector, cap, ratios)
   - `CompanyDetailSchema` (full profile + KPIs + executives + holders)
   - `FinancialHistorySchema` (multi-year statements array)

4. `api/schemas/screening.py`:
   - `ScreeningFiltersSchema` (request body for filtering)
   - `ScreeningResultSchema` (paginated list of CompanyRowSchema)
   - `SnapshotSchema`

5. `api/schemas/scoring.py`:
   - `ScoreBreakdownSchema` (total, quality, value, growth, risk + drivers)
   - `ScoreDriverSchema` (metric name, contribution, direction)

6. `api/schemas/watchlist.py`:
   - `WatchlistEntrySchema`
   - `AnalystMemoSchema` (thesis, risks, catalysts, valuation, next action)

7. `api/schemas/signals.py`:
   - `SignalSchema` (ticker, signal type, previous value, current value, delta)
   - `MoversSchema` (score movers up/down since last snapshot)

8. `api/routers/screening.py`: implement all screening endpoints.

9. `api/routers/companies.py`: implement company detail, score, history,
   peers endpoints.

10. `api/routers/watchlist.py`: implement CRUD watchlist endpoints.

11. `api/routers/data_refresh.py`: implement refresh trigger endpoints with
    progress via Server-Sent Events (SSE) — use `sse-starlette` library.

12. `api/routers/signals.py`: implement signals endpoint (movers, top scores).

13. Write integration tests in `tests/api/` for each router — use
    `httpx.AsyncClient` with `TestClient`. Test happy path + error cases
    (404 for unknown ticker, 422 for invalid filters).

**Definition of done:**
- [ ] All endpoints return correct Pydantic schemas.
- [ ] `GET /api/screening/universe` returns a valid list with real data.
- [ ] `GET /api/companies/{ticker}/score` returns full score breakdown.
- [ ] API tests pass.
- [ ] FastAPI auto-docs at `/docs` show all endpoints correctly typed.
- [ ] No business logic added in routers.

---

### Phase 2 — Workspace shell & panel engine

**Branch:** `feat/workspace-shell`

**Goal:** Build the terminal layout engine. The workspace loads with a default
layout (split-h: Screener + Tearsheet). Panels can be switched by type. No
real data yet — use mocked/static data to validate the layout system.

**Tasks:**

1. `frontend/src/context/WorkspaceContext.tsx`:
   - Define `WorkspaceState` interface (see Panel system design section).
   - Implement `WorkspaceProvider` with `useState` for `activeTicker` and
     `layout`.
   - Persist layout to `localStorage`.

2. `frontend/src/workspace/Workspace.tsx`:
   - Import `PanelGroup`, `Panel`, `PanelResizeHandle` from
     `react-resizable-panels`.
   - Render panels based on current layout from context.
   - Support horizontal and vertical splits, and the quad preset.

3. `frontend/src/workspace/Panel.tsx`:
   - Panel shell: header bar + body.
   - Header: panel type label, dropdown to switch panel type, close button.
   - Body: renders the registered panel component for the current type.

4. `frontend/src/panels/registry.ts`:
   - Define `PanelType` union type.
   - Define `PanelDefinition` interface.
   - Export `PANEL_REGISTRY` with all known panel types mapped to placeholder
     components.

5. `frontend/src/workspace/LayoutPresets.ts`:
   - Define `single`, `split-h`, `split-v`, `quad` presets as typed objects.

6. `frontend/src/workspace/PanelHeader.tsx`:
   - Toolbar with layout preset buttons (icons: single square, two columns,
     two rows, 2×2 grid).
   - Active preset highlighted.

7. `frontend/src/App.tsx`:
   - Wrap app in `QueryClientProvider` and `WorkspaceProvider`.
   - Render `Workspace` as the single root component.

8. `frontend/src/lib/constants.ts`:
   - Terminal color palette:
     ```
     BG_BASE:      #0a0a0f    (deepest background)
     BG_PANEL:     #0f0f1a    (panel background)
     BG_ELEVATED:  #161625    (card/table row hover)
     BORDER:       #1e1e35    (panel borders)
     TEXT_PRIMARY: #e2e8f0
     TEXT_MUTED:   #64748b
     ACCENT:       #3b82f6    (Bloomberg blue)
     POSITIVE:     #22c55e
     NEGATIVE:     #ef4444
     WARNING:      #f59e0b
     ```
   - Score thresholds:
     ```
     SCORE_HIGH:   70   (green)
     SCORE_MID:    45   (amber)
     SCORE_LOW:    0    (red)
     ```

9. `frontend/src/lib/api.ts`:
   - Typed fetch wrapper using `VITE_API_BASE_URL` env var.
   - Standard error handling: throw `ApiError` with status + message.
   - No business logic here — pure HTTP client.

**Definition of done:**
- [ ] App renders with two resizable side-by-side panels.
- [ ] Panel type can be switched via header dropdown.
- [ ] Layout preset buttons change the workspace arrangement.
- [ ] Layout persists across page refresh via localStorage.
- [ ] Terminal dark theme applied globally.
- [ ] No real API calls yet — placeholder "Panel: screener" text is fine.

---

### Phase 3 — Screener panel

**Branch:** `feat/panel-screener`

**Goal:** Build the Screener panel. Analysts see the full universe in a dense
sortable table with live filters. Clicking a row sets `activeTicker` in context.

**Tasks:**

1. `frontend/src/hooks/useScreening.ts`:
   - `useUniverse(filters)`: React Query hook for `GET /api/screening/universe`.
   - `useSnapshots()`: React Query hook for `GET /api/screening/snapshots`.
   - All types derived from Pydantic schemas (generate or write manually).

2. `frontend/src/panels/ScreenerPanel/ScreenerPanel.tsx`:
   - Main panel component. Renders filter sidebar + data table.
   - On row click: `setActiveTicker(ticker)` from context.

3. `frontend/src/panels/ScreenerPanel/ScreenerTable.tsx`:
   - Dense table using shadcn/ui `Table` + Tailwind.
   - Columns: Ticker, Name, Score, Sector, Market Cap, P/E, EV/EBITDA, ROE,
     Rev Growth, Net Debt/EBITDA.
   - Score column: render `ScoreBadge` component (colored 0-100 badge).
   - Numeric cells: green if favorable, red if unfavorable (thresholds in
     `constants.ts`).
   - Sortable columns (client-side sort on loaded data).
   - Row highlight on hover + active row highlight when ticker matches
     `activeTicker`.

4. `frontend/src/panels/ScreenerPanel/ScreenerFilters.tsx`:
   - Collapsible sidebar.
   - Filters: Sector (select), Market Cap range (min/max), Score range,
     Watchlist only (checkbox), Sort by (select).
   - Debounced inputs: 300ms delay before triggering refetch.
   - "Reset filters" button.

5. `frontend/src/components/ScoreBadge.tsx`:
   - Shared component. Props: `score: number`.
   - Color: green (≥70), amber (45-69), red (<45).
   - Font: monospace, bold.

6. `frontend/src/components/MetricCell.tsx`:
   - Shared component. Props: `value: number | null`, `type: MetricType`,
     `format: "ratio" | "percent" | "currency"`.
   - Applies directional color coding based on threshold in constants.ts.
   - Shows `—` for null values.

**Definition of done:**
- [ ] Screener table renders with real data from API.
- [ ] Filters work and trigger API refetch.
- [ ] Score badge correctly colored.
- [ ] Numeric metrics color-coded.
- [ ] Clicking a row sets `activeTicker` in context.
- [ ] Loading and error states handled gracefully.
- [ ] No business logic in components (thresholds from constants.ts only).

---

### Phase 4 — Tearsheet panel

**Branch:** `feat/panel-tearsheet`

**Goal:** Build the Company Tearsheet panel. Reacts to `activeTicker` from
context. Shows score breakdown, financial history, charts, and peer comparison.

**Tasks:**

1. `frontend/src/hooks/useCompany.ts`:
   - `useCompanyDetail(ticker)`: React Query hook.
   - `useCompanyScore(ticker)`: React Query hook.
   - `useFinancialHistory(ticker)`: React Query hook.
   - `useCompanyPeers(ticker)`: React Query hook.
   - All hooks skip fetch when `ticker` is null.

2. `frontend/src/panels/TearsheetPanel/TearsheetPanel.tsx`:
   - Watches `activeTicker` from context.
   - Shows placeholder "Select a company" when `activeTicker` is null.
   - Tab navigation: Summary | Financials | Charts | Peers.

3. `frontend/src/panels/TearsheetPanel/TearsheetHero.tsx`:
   - Company name, ticker, market, currency.
   - Current price, market cap.
   - `ScoreBadge` prominent.
   - 4 key metrics in a row: best metric per sub-score category.
   - Sector + industry tags.

4. `frontend/src/panels/TearsheetPanel/ScoreBreakdown.tsx`:
   - 4 sub-score bars (Quality, Value, Growth, Risk) with numeric values.
   - Overall score prominent at top.
   - Positive drivers: top 3 metrics contributing most (green arrow + metric
     name + value).
   - Negative drivers: top 3 metrics dragging score (red arrow + metric name
     + value).
   - This component is the **core differentiator** — make it visually clear
     and readable.

5. `frontend/src/panels/TearsheetPanel/FinancialsTable.tsx`:
   - Multi-year financial table (up to 5 years).
   - Rows: Revenue, EBITDA, Net Income, FCF, Total Assets, Net Debt.
   - Columns: each fiscal year.
   - Color code YoY change: green = growth, red = decline.
   - CAGR column at the end.

6. `frontend/src/panels/TearsheetPanel/TearsheetCharts.tsx`:
   - Use TradingView Lightweight Charts for price history (area chart).
   - Use Recharts for Revenue + EBITDA bar chart (grouped by year).
   - Charts must be responsive (ResizeObserver on container).

7. `frontend/src/panels/TearsheetPanel/PeersTable.tsx`:
   - Table of sector peers with same columns as ScreenerTable.
   - Active company row highlighted.
   - Percentile rank shown per metric (e.g., "P/E: 32nd percentile").

**Definition of done:**
- [ ] Panel updates when `activeTicker` changes in context.
- [ ] Score breakdown shows correct sub-scores + drivers.
- [ ] Financial table shows multi-year history with color-coded changes.
- [ ] Price chart renders and is interactive (crosshair, zoom).
- [ ] Peers table shows sector comparison with percentile ranks.
- [ ] No data fetching in sub-components — all via hooks in parent.

---

### Phase 5 — Watchlist panel

**Branch:** `feat/panel-watchlist`

**Goal:** Build the Watchlist panel. Analysts track companies with status,
analyst memos, and next review dates.

**Tasks:**

1. `frontend/src/hooks/useWatchlist.ts`:
   - `useWatchlist()`: React Query hook for `GET /api/watchlist`.
   - `useAddToWatchlist()`: mutation.
   - `useRemoveFromWatchlist()`: mutation.
   - `useUpdateMemo()`: mutation.
   - All mutations invalidate the watchlist query on success.

2. `frontend/src/panels/WatchlistPanel/WatchlistPanel.tsx`:
   - List of watchlisted companies with status badges.
   - Click a company → sets `activeTicker` in context AND opens memo editor.

3. `frontend/src/panels/WatchlistPanel/WatchlistRow.tsx`:
   - Company name, ticker, `ScoreBadge`, status badge, next review date.
   - Status badge variants: Watching (blue), Review (amber), Conviction (green),
     Rejected (red/muted).

4. `frontend/src/panels/WatchlistPanel/AnalystMemo.tsx`:
   - Inline editable fields: Thesis, Risks, Catalysts, Valuation notes,
     Next action.
   - Auto-save on blur (debounced PATCH to API).
   - Visual indicator when saved ("Saved ✓" fades out after 1.5s).

5. `frontend/src/panels/WatchlistPanel/WatchlistStatusSelect.tsx`:
   - Dropdown to change company status.
   - Triggers PATCH request + optimistic update.

6. Add "Add to Watchlist" button in TearsheetPanel hero area (Phase 4
   component). Button calls `useAddToWatchlist` mutation. Toggle to "Remove"
   if already in watchlist.

**Definition of done:**
- [ ] Watchlist renders all tracked companies.
- [ ] Status can be changed and persists.
- [ ] Analyst memo auto-saves.
- [ ] Add/remove from watchlist works from both Watchlist panel and Tearsheet.
- [ ] Clicking a company in watchlist sets `activeTicker`.

---

### Phase 6 — Signals panel

**Branch:** `feat/panel-signals`

**Goal:** Build the Signals panel — the highest-value view. Shows what has
changed since the last snapshot, what is worth looking at now, and what has
deteriorated. This turns the screener into a decision-support tool.

**Tasks:**

1. Implement `GET /api/signals` in the FastAPI layer:
   - Pull last two snapshots from `ScreeningService`.
   - Compute score movers (delta ≥ 5 points): `SignalSchema`.
   - Top 5 by quality sub-score.
   - Top 5 by value sub-score.
   - Watchlist companies with significant score change.
   - Return a `SignalsSchema` grouping all of the above.

2. `frontend/src/hooks/useSignals.ts`:
   - `useSignals()`: React Query hook. Refresh every 5 minutes.

3. `frontend/src/panels/SignalsPanel/SignalsPanel.tsx`:
   - Sections: Score Movers ↑ | Score Movers ↓ | Top Quality | Top Value |
     Watchlist Alerts.
   - Each section is a compact list.

4. `frontend/src/panels/SignalsPanel/SignalRow.tsx`:
   - Company ticker, name, score badge.
   - Delta indicator: `+7 pts` (green) or `-5 pts` (red).
   - Click → sets `activeTicker` in context.

5. `frontend/src/panels/SignalsPanel/SectionHeader.tsx`:
   - Section title + count badge.
   - Collapsible (chevron toggle).

**Definition of done:**
- [ ] Signals panel shows movers computed from snapshot diffs.
- [ ] Top Quality and Top Value sections populated.
- [ ] Watchlist alerts shown when score changed for tracked company.
- [ ] Click on any signal sets `activeTicker`.
- [ ] Panel refreshes automatically every 5 minutes.

---

### Phase 7 — Data refresh panel & UX polish

**Branch:** `feat/ux-polish`

**Goal:** Close UX gaps. Add keyboard navigation, data refresh UI, and minor
quality-of-life improvements.

**Tasks:**

1. **Data refresh flow:**
   - Add `feat/data-refresh-panel` sub-task if needed.
   - `POST /api/companies/refresh` with SSE progress stream.
   - `RefreshPanel` or modal: shows per-company progress, errors, completion.
   - Uses `EventSource` in frontend to consume the SSE stream.

2. **Keyboard shortcuts** (global, via `useEffect` on `document`):
   - `S` — focus Screener panel filter input.
   - `W` — focus Watchlist panel.
   - `J` / `K` — navigate rows in focused table (up/down).
   - `Enter` — open tearsheet for selected row.
   - `Esc` — clear `activeTicker`.
   - Shortcuts shown in a `?` modal.

3. **Screener table virtualization:**
   - If universe exceeds 200 rows, use `@tanstack/react-virtual` for the table
     body to maintain performance.

4. **Empty and error states:**
   - Each panel must handle: loading skeleton, empty state (no data), error
     state (API unreachable) with retry button.
   - Use consistent `LoadingState` and `ErrorState` shared components.

5. **Toast notifications:**
   - Use shadcn/ui `Sonner` for: data refresh complete, watchlist add/remove,
     save success, API errors.
   - No alerts or `window.confirm`.

6. **Score breakdown animation:**
   - Animate sub-score bars on mount and on ticker change (CSS transition).

7. **Tearsheet export:**
   - "Export tearsheet" button in TearsheetPanel header.
   - `GET /api/companies/{ticker}/export` — returns CSV of KPIs and history.
   - Frontend triggers download via `<a download>` tag.

**Definition of done:**
- [ ] Keyboard shortcuts work globally.
- [ ] All panels have loading and error states.
- [ ] Data refresh shows per-company progress.
- [ ] Toast notifications appear for key actions.
- [ ] No `console.log` in committed code.
- [ ] Large universes (200+ rows) do not cause visible lag.

---

## What agents must never do

- **Never modify any file in `src/`** unless the task explicitly says so.
- **Never add auth, login, or user management.** Not even "just a basic token."
- **Never add business logic to the frontend.** All calculations, scoring,
  filtering stay in Python services.
- **Never call SQLAlchemy models from the API layer directly.** Only call
  services. Services call repositories. Repositories touch the DB.
- **Never create a new service** to bypass an existing one. Read
  `src/services/` first.
- **Never use `any` in TypeScript.** If the type is unknown, derive it from
  the API schema or open a question.
- **Never fetch data inside a sub-component.** Data fetching only in top-level
  panel components via hooks.
- **Never skip a phase.** Each phase builds on the previous one. Phases 3-6
  depend on Phase 2 (workspace shell). Phase 1 (API) must be complete and
  tested before Phase 3.

---

## Running the full stack (development)

```bash
# Terminal 1 — Python API
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — React frontend
cd frontend && pnpm dev
```

Frontend proxies `/api/*` to `http://localhost:8000` via Vite's `proxy` config
in `vite.config.ts`. No CORS issues in development.

---

## Adding a new panel in the future

1. Create `frontend/src/panels/YourPanel/YourPanel.tsx`.
2. Add one entry to `PANEL_REGISTRY` in `panels/registry.ts`.
3. If new data is needed, add an endpoint in `api/routers/` and a hook in
   `frontend/src/hooks/`.
4. No changes required to the workspace layout engine.

That is the entire extension protocol.
