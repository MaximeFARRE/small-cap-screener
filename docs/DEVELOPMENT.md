# Development Workflow

This document describes the expected workflow for contributing to this project.

The objective is to keep the repository clean, predictable, and easy to maintain.

---

## 0. First-Time Setup

After cloning, activate the virtual environment, install dependencies, and enable hooks:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pre-commit install
```

---

## 1. Branch Strategy

Never work directly on `main`.

Use one dedicated documentation branch for documentation updates:

```text
docs/update-docs
```

Use dedicated feature branches for major functional work:

```text
feat/<description>
```

Use dedicated fix branches for bug fixes:

```text
fix/<description>
```

Allowed branch patterns:

```text
feat/<description>
fix/<description>
docs/<description>
chore/<description>
test/<description>
refactor/<description>
```

Before switching to another branch, always:

1. Commit current changes.
2. Push current branch.
3. Verify `git status` is clean.

Example:

```bash
git status
git add <files>
git commit -m "docs: update development branch policy"
git push
git checkout feat/my-feature
```

---

## 2. Read Before Editing

Before changing a file:

- Read the existing implementation.
- Understand the current architecture.
- Check whether the logic already exists elsewhere.
- Avoid creating duplicate functionality.

Always check:

- `README.md`
- `AGENTS.md`
- `CLAUDE.md`
- `docs/ARCHITECTURE.md`

---

## 3. Small, Incremental Changes

Prefer multiple small commits over one large commit.

Good workflow:

1. Create or update one file.
2. Test it.
3. Commit it.
4. Move to the next logical change.

Bad workflow:

- Modify many files at once.
- Mix documentation, refactor, and features in the same commit.
- Rewrite a large file unnecessarily.

---

## 4. Commit Frequently

Commit after every logical step.

Examples:

```bash
git add src/services/import_service.py
git commit -m "feat: add import validation service"
```

```bash
git add README.md docs/ARCHITECTURE.md
git commit -m "docs: improve project documentation"
```

A commit should represent one idea.

---

## 5. Conventional Commit Format

Always use one of these prefixes:

```text
feat:
fix:
docs:
chore:
test:
refactor:
```

Examples:

```text
feat: add user authentication service
fix: prevent duplicate transaction import
docs: update readme installation section
chore: update .gitignore
test: add tests for portfolio service
refactor: move validation logic into service layer
```

---

## 6. Respect the Architecture

Architecture must remain:

```text
UI → Services → Repository / DB
```

Rules:

- No business logic in UI files.
- No database calls in UI files.
- No SQL or API logic in services unless explicitly intended.
- No duplicated logic.

Before creating a new file:

- Check if an existing file can be reused.
- Prefer extending an existing service.
- Avoid unnecessary files.

---

## 7. Before Creating a Pull Request

Run the following checks:

```bash
git status
git diff
```

Verify:

- Only expected files were modified.
- No unrelated changes remain.
- No secrets or `.env` files are included.
- Documentation is updated if needed.

Recommended checks:

```bash
pytest
ruff check .
black --check .
```

---

## 8. Documentation Rules

Documentation must be updated when:

- A new feature is added.
- Installation changes.
- Architecture changes.
- Important limitations are discovered.

Files to keep updated:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `CHANGELOG.md`

---

## 9. Refactoring Rules

Refactoring is allowed only if:

- It clearly improves readability or architecture.
- It does not change behavior.
- It remains small and isolated.

If a refactor is large:

- Split it into multiple commits.
- Keep feature work separate.
- Document the reason in the commit message.

Bad example:

```text
feat: add import feature and refactor whole project
```

Good example:

```text
refactor: move import logic into dedicated service
feat: add csv import feature
```

---

## 10. Final Checklist Before Merging

- [ ] Work was done on a dedicated branch.
- [ ] Commits are small and clean.
- [ ] Architecture rules are respected.
- [ ] No unrelated files were modified.
- [ ] Tests pass.
- [ ] Documentation is updated.
- [ ] `git diff` was reviewed.
- [ ] The branch is ready to merge into `main`.
- [ ] Current branch was pushed before branch switching.

---

## Desktop Packaging (Windows)

Minimal reproducible build:

```bash
pip install -r requirements-dev.txt
python -m PyInstaller --clean --noconfirm small_cap_screener.spec
```

Executable output:

```text
dist/small-cap-screener/small-cap-screener.exe
```
