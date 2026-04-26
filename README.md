# Small Cap Screener

Desktop application for screening and analyzing French small-cap companies.

The goal is to provide a **simple, reliable and extensible tool** to:

* collect and store financial data
* compute key financial ratios
* rank companies using multi-factor scoring
* generate actionable investment insights

---

## Features (MVP)

* Local database of companies and financial data
* Financial ratios (valuation, quality, growth, risk)
* Multi-factor scoring (quality, value, growth, risk)
* Screening and filtering
* Export (CSV / Excel)

---

## Stack

* Python (pandas, numpy)
* PySide6 (desktop UI)
* SQLite + SQLAlchemy
* pytest, ruff, black, pre-commit

See `STACK.md` for details.

---

## Releases

Automated releases are managed with `python-semantic-release` from Conventional Commits.

See `docs/RELEASE.md`.

---

## Architecture

```
UI → Services → Repositories
```

* UI: display and interaction only
* Services: business logic (ratios, scoring)
* Repositories: data access (DB, APIs)

See `docs/ARCHITECTURE.md`.

---

## Getting Started

```bash
# clone the repository
git clone <repo-url>
cd small-cap-screener

# create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# install dependencies
pip install -r requirements.txt

# enable pre-commit
pre-commit install
```

---

## Project Structure

```
src/
  ui/
  services/
  repositories/
```

---

## Roadmap

See `docs/ROADMAP.md`.

---

## Notes

* Local-first application (no server)
* Designed for maintainability and scalability
* Compatible with AI-assisted development workflows
