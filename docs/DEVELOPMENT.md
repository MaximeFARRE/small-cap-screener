# DEVELOPMENT.md

# Development Workflow

This document describes the expected workflow for contributing to this project.

The objective is to keep the repository clean, predictable, and easy to maintain.

---

## 1. Never Work on `main`

The `main` branch must always stay stable and deployable.

Before starting any work:

```bash id="yo06v5"
git branch
git checkout -b feat/my-feature
````

Allowed branch patterns:

```text id="w0tt1y"
feat/<description>
fix/<description>
docs/<description>
chore/<description>
test/<description>
refactor/<description>
```

Examples:

```text id="n1u3lq"
feat/add-import-service
fix/correct-login-validation
docs/update-readme
```

---

## 2. Read Before Editing

Before changing a file:

* Read the existing implementation
* Understand the current architecture
* Check whether the logic already exists elsewhere
* Avoid creating duplicate functionality

Always check:

* `README.md`
* `AGENTS.md`
* `CLAUDE.md`
* `docs/ARCHITECTURE.md`

---

## 3. Small, Incremental Changes

Prefer multiple small commits over one large commit.

Good workflow:

1. Create or update one file
2. Test it
3. Commit it
4. Move to the next logical change

Bad workflow:

* Modify 20 files at once
* Mix documentation, refactor, and features in the same commit
* Rewrite a large file unnecessarily

---

## 4. Commit Frequently

Commit after every logical step.

Examples:

```bash id="x3kr24"
git add src/services/import_service.py
git commit -m "feat: add import validation service"
```

```bash id="vpb9sd"
git add README.md docs/ARCHITECTURE.md
git commit -m "docs: improve project documentation"
```

A commit should ideally represent one idea.

---

## 5. Conventional Commit Format

Always use one of these prefixes:

```text id="w53qgh"
feat:
fix:
docs:
chore:
test:
refactor:
```

Examples:

```text id="xam8cl"
feat: add user authentication service
fix: prevent duplicate transaction import
docs: update README installation section
chore: update .gitignore
test: add tests for portfolio service
refactor: move validation logic into service layer
```

---

## 6. Respect the Architecture

Architecture must remain:

```text id="72h6tq"
UI → Services → Repository / DB
```

Rules:

* No business logic in UI files
* No database calls in UI files
* No SQL or API logic in services unless explicitly intended
* No duplicated logic

Before creating a new file:

* Check if an existing file can be reused
* Prefer extending an existing service
* Avoid unnecessary files

---

## 7. Before Creating a Pull Request

Run the following checks:

```bash id="5v3zvv"
git status
git diff
```

Verify:

* Only expected files were modified
* No unrelated changes remain
* No secrets or `.env` files are included
* Documentation is updated if needed

Recommended checks:

```bash id="cc1kmd"
# Python
pytest

# Node.js
npm test

# Formatting
ruff check .
black .
npm run lint
```

Adapt the commands to the current project.

---

## 8. Documentation Rules

Documentation must be updated when:

* A new feature is added
* Installation changes
* Architecture changes
* Important limitations are discovered

Files to keep updated:

* `README.md`
* `docs/ARCHITECTURE.md`
* `docs/ROADMAP.md`
* `CHANGELOG.md`

---

## 9. Refactoring Rules

Refactoring is allowed only if:

* It clearly improves readability or architecture
* It does not change behavior
* It remains small and isolated

If a refactor is large:

* Split it into multiple commits
* Keep feature work separate
* Document the reason in the commit message

Bad example:

```text id="paznjs"
feat: add import feature and refactor whole project
```

Good example:

```text id="p3fnyv"
refactor: move import logic into dedicated service
feat: add CSV import feature
```

---

## 10. Final Checklist Before Merging

* [ ] Work was done on a dedicated branch
* [ ] Commits are small and clean
* [ ] Architecture rules are respected
* [ ] No unrelated files were modified
* [ ] Tests pass
* [ ] Documentation is updated
* [ ] `git diff` was reviewed
* [ ] The branch is ready to merge into `main`

```
```
