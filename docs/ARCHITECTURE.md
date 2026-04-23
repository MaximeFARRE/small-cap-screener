# Architecture

This project follows a **strict layered architecture** to keep the code maintainable, testable, and scalable.

The system is designed for a **desktop financial analysis application** (small-cap screener) with a local-first approach.

---

## Core Rule

```
UI / Components / Views
        ↓
Services / Business Logic
        ↓
Repositories / Database / External Data
```

Each layer has a single responsibility.

---

## 1. UI Layer

Examples:

* Desktop views (PySide6)
* Tables, filters, forms
* Controllers linked to UI events

Responsibilities:

* Display data
* Handle user interaction
* Trigger actions
* Call services

Rules:

* No business logic
* No financial calculations
* No SQL queries
* No API calls

---

## 2. Services Layer

Examples:

* Ratio calculations
* Scoring logic
* Screening logic
* Data transformations

Responsibilities:

* Centralize all business logic
* Provide a clean API to UI
* Combine multiple repositories

Rules:

* No UI code
* No direct DB queries
* Reuse existing logic

Example:

```
ScreeningService
├── compute_ratios()
├── compute_scores()
├── filter_universe()
└── get_top_picks()
```

---

## 3. Repository Layer

Examples:

* Database access (SQLite / SQLAlchemy)
* External API calls (httpx)
* File loading / saving

Responsibilities:

* Read/write data
* Isolate external systems

Rules:

* No business logic
* Only data access

---

## Data Flow

```
External APIs → Repositories → Services → UI
                       ↓
                   Database
```

---

## Single Source of Truth

Each feature must have one owner service.

Examples:

```
Company data       → CompanyService
Financial data     → FinancialService
Ratios            → RatioService
Scoring           → ScoreService
Screening         → ScreeningService
```

Avoid duplicated logic across files.

---

## File Creation Rules

Before creating a new file:

* Check if logic already exists
* Prefer extending existing services
* Avoid duplicates

---

## Dependency Direction

```
UI → Services → Repositories
```

Never:

* UI → Repository directly
* Services → UI
* Repository → Services (business logic)

---

## Refactoring Policy

* Prefer small changes
* Avoid large rewrites
* Keep behavior unchanged

---

## Recommended Structure

```
src/
├── ui/
├── services/
├── repositories/
├── models/
├── utils/
└── tests/
```

---

## Final Rule

If unsure:

* UI = display
* Service = logic
* Repository = data

Keep business logic out of the UI.
