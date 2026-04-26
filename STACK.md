# STACK.md

## Overview

Desktop financial analysis app (small-cap screener).

Principles:

* Local-first (no server)
* Simple, modular, maintainable
* Compatible with AI-assisted coding

Architecture:
UI → Services → Repositories

---

## Core

* Python 3.11+
* pandas
* numpy

---

## UI

* PySide6

Rules:

* UI = display + interaction only
* No business logic in UI

---

## Data

* SQLite
* SQLAlchemy

Rules:

* All DB access via repositories

---

## External Data

* httpx

Rules:

* API calls only in repositories

---

## Testing

* pytest

---

## Code Quality

* ruff (linting and formatting)
* pre-commit (automation)

---

## Config

* python-dotenv
* pyyaml

---

## Export

* pandas (CSV)
* xlsxwriter (Excel)

---

## Not Included

* No web backend
* No cloud
* No microservices

---

## Optional (later)

* scipy
* AI tools (external only)
