# Development Workflow (v2)

This document defines the expected workflow for contributing to the v2 architecture (React frontend + FastAPI backend).

## 1. Setup

## Python environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
```

## Frontend environment

```bash
cd frontend
npm install
cd ..
```

## 2. Run Locally

Run API:

```bash
.venv\Scripts\activate
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Run frontend:

```bash
cd frontend
npm run dev
```

## 3. Branching and Commits

Never work on `main`.

Allowed branch patterns:
- `feat/<description>`
- `fix/<description>`
- `docs/<description>`
- `chore/<description>`
- `test/<description>`
- `refactor/<description>`

Commit format:

```text
feat|fix|docs|chore|test|refactor: short description
```

For major releases, use Conventional Commit breaking syntax:

```text
type!: short description
```

or commit footer:

```text
BREAKING CHANGE: ...
```

## 4. Architecture Rules

Architecture flow:

```text
frontend -> api -> services -> repositories
```

Rules:
- no business logic in frontend
- no repository calls from API routers
- no persistence logic in services

## 5. Quality Checks

Backend:

```bash
ruff check .
ruff format --check .
pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

## 6. Before Opening PR

- review `git status`
- review `git diff`
- ensure only related files are changed
- update docs if behavior/architecture changed

Core docs to keep aligned:
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/KNOWN_LIMITATIONS.md`
- `CHANGELOG.md`
