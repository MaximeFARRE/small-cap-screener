````md id="v4w58o"
# CONTRIBUTING.md

# Contributing

Thank you for contributing to this project.

Please keep changes small, focused, and consistent with the existing architecture.

---

## Setup

```bash
# Clone the repository
git clone <repository-url>
cd <repository-name>

# Enable git hooks (required — blocks direct commits to main)
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit   # macOS / Linux only

# Fix for AI agents (Codex) — git "dubious ownership" permission error
git config --global --add safe.directory '*'

# Create a virtual environment if relevant
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

If the project uses another stack (Node.js, C++, etc.), adapt the setup commands accordingly.

---

## Branches

Never work directly on `main`.

Use a dedicated branch:

| Type          | Pattern               |
| ------------- | --------------------- |
| Feature       | `feat/<description>`  |
| Bug fix       | `fix/<description>`   |
| Documentation | `docs/<description>`  |
| Chore         | `chore/<description>` |
| Tests         | `test/<description>`  |

Examples:

```text
feat/add-user-authentication
fix/correct-date-format
docs/update-readme
```

---

## Commits

Use Conventional Commits:

```text
feat: add transaction import service
fix: prevent duplicate records
docs: rewrite README
chore: update .gitignore
test: add unit tests for import service
```

Rules:

* Commit after each logical step
* Keep commits small and focused
* Do not mix unrelated changes in the same commit

---

## Architecture

Always keep a clear separation of concerns:

```text
UI / pages / components
        ↓
services / business logic
        ↓
repositories / api / database
```

Rules:

* UI files only handle display and interaction
* Business logic belongs in `services/`
* Database and API access belong in `repositories/`, `db/`, or equivalent
* Never put business logic in UI files
* Never duplicate existing logic
* Reuse existing files before creating new ones

---

## Pull Requests

Before opening a pull request:

* [ ] The branch is not `main`
* [ ] Commits are clean and descriptive
* [ ] No unrelated files were modified
* [ ] Documentation was updated if necessary
* [ ] Tests pass if the project contains tests
* [ ] The architecture rules above are still respected

```
```
