# ARCHITECTURE.md

# Architecture

This project follows a strict layered architecture to keep the code maintainable, testable, and easy to evolve.

The goal is to avoid large refactors, duplicated logic, and tightly coupled files.

---

## Core Rule

```text id="sz5zwu"
UI / Components / Pages
            ↓
Services / Business Logic
            ↓
Repositories / Database / API / External Sources
````

Each layer has a single responsibility.

---

## 1. UI Layer

Examples:

* Pages
* Components
* Views
* Screens
* Controllers directly linked to the interface

Responsibilities:

* Display data
* Handle user interactions
* Trigger actions
* Call services

The UI layer must never:

* Contain business logic
* Execute SQL queries
* Access the database directly
* Call external APIs directly
* Duplicate calculations or validation rules

Bad example:

```text id="frz7ik"
button_click():
    price = quantity * product.price * 1.2
    db.execute("INSERT INTO orders ...")
```

Good example:

```text id="8ksjlb"
button_click():
    order_service.create_order(...)
```

---

## 2. Services Layer

Examples:

* Business rules
* Validation
* Calculations
* Data transformations
* Coordination between multiple repositories or APIs

Responsibilities:

* Centralize all business logic
* Expose a clear API to the UI
* Reuse existing logic
* Become the single source of truth for the project

Rules:

* A feature should have one main service responsible for it
* Services may call repositories or other services
* Services must not depend on UI code

Example:

```text id="d0mktj"
OrderService
├── validate_order()
├── calculate_total()
├── create_order()
└── cancel_order()
```

---

## 3. Repository / Data Layer

Examples:

* Database access
* SQL queries
* ORM logic
* External API calls
* File loading / saving

Responsibilities:

* Read and write data
* Isolate persistence and external systems
* Return clean data structures to services

Rules:

* Repositories must not contain business logic
* Repositories should only perform data access
* SQL, HTTP requests, file I/O, and external integrations belong here

Bad example:

```text id="g59f6d"
SELECT all users
IF age > 18 THEN send email
```

Good example:

```text id="4z5x1l"
users = user_repository.get_all()
adult_users = user_service.filter_adults(users)
```

---

## Single Source of Truth

Each feature should have one clear owner.

Example:

```text id="gzy4mo"
User data           → UserService
Authentication      → AuthService
Portfolio analysis  → PortfolioService
Import logic        → ImportService
```

Avoid:

* Same logic copied in several files
* Same calculation implemented twice
* UI files creating their own rules

If a rule already exists in a service, reuse it.

---

## File Creation Policy

Before creating a new file:

* Check if an existing file already has the correct responsibility
* Prefer extending an existing service instead of creating duplicates
* Only create a new file if it clearly improves clarity or separation

Avoid:

* `new_service_v2.py`
* `helper_final.py`
* `utils_temp.ts`

Use clear, explicit names:

```text id="w4m76m"
auth_service.py
portfolio_repository.py
transaction_validator.ts
```

---

## Dependency Direction

Dependencies must always go in one direction:

```text id="0txa5h"
UI → Services → Repositories
```

Never:

```text id="7ut7ia"
Repository → UI
Service → UI
UI → Repository directly
```

---

## Refactoring Policy

This project favors small and safe changes.

Rules:

* Make the smallest change possible
* Preserve the current architecture
* Do not rewrite large files without a strong reason
* Avoid broad refactors during feature work
* Refactor only when the gain is clear and immediate

If a large refactor is needed:

1. Document the reason
2. Split it into several small commits
3. Keep behavior unchanged
4. Update the documentation

---

## Commit Discipline

Every architectural change must be committed separately.

Examples:

```text id="hjlwmn"
feat: add portfolio service
fix: move validation from UI to service
refactor: isolate database access into repository
docs: update architecture documentation
```

Do not mix:

* Architecture changes
* Feature work
* Formatting only
* Documentation only

---

## Recommended Project Structure

```text id="g7f0o5"
src/
├── ui/
├── services/
├── repositories/
├── db/
├── models/
├── utils/
└── tests/
```

Possible variants depending on the stack are acceptable, as long as the separation of concerns remains clear.

---

## Final Rule

If you hesitate where code belongs:

* UI = display and interaction
* Service = decision and business logic
* Repository = data access

When in doubt, keep business logic out of the UI.

```
```
