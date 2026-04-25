# AGENTS.md — Agent Operating Manual

Read this file **and `STACK.md`** before making any change.

---

## Workflow

1. Read existing code and docs before touching anything.
2. `git branch` — never work on `main`.
3. Create a branch: `feat/`, `fix/`, `docs/`, `chore/`, `test/`.
4. Make small, focused changes. One concern per task.
5. Commit after each logical step.
6. Push your current branch before switching to another branch.
7. Review `git diff` before finishing.

---

## Architecture

```
UI / pages / components
        ↓
services / business logic
        ↓
repositories / api / database
```

- UI = display and user interaction only.
- Services = all business logic, calculations, decisions.
- Repositories = all DB queries and external API calls.
- Never cross layers. Never put logic in UI. Never mix persistence and business logic.
- Reuse an existing service before creating a new one.
- Do not duplicate logic across files.

---

## Code quality

- Use explicit types and annotations (type hints, TypeScript types, etc.).
- No magic strings or numbers — use named constants.
- No silent error handling: no `except: pass`, no empty `catch {}`, no swallowed exceptions.
- No `print()` / `console.log()` in committed code.
- Functions do one thing. Max ~40 lines per function.
- Explicit, descriptive names. Avoid abbreviations.
- Validate inputs only at system boundaries (user input, external APIs). Trust internal code.
- No hardcoded credentials or secrets. Use environment variables.
- No TODO or FIXME in committed code — create a tracked issue instead.
- If behavior is ambiguous, state assumptions explicitly before writing code.

---

## Changes

- Prefer targeted edits over full rewrites.
- Do not rewrite a file if a small edit is enough.
- Do not perform broad refactors unless explicitly requested.
- Do not modify unrelated files.
- Create a new file only if no existing file is suitable.
- Never rename or delete files without a clear reason.

---

## Commits

Format: `feat|fix|docs|chore|test: <what and why in one line>`

- One logical change = one commit.
- Never batch unrelated changes in one commit.
- Never leave many modified files uncommitted.
- Commit and push before switching branches.

---

## Never do

- Commit directly to `main`.
- Invent implementation details without reading the code first.
- Silently change architecture.
- Create unnecessary files.
- Mix unrelated fixes in one task.
- Claim something was tested if it was not actually run.

---

## Definition of done

Before finishing:

- [ ] Correct branch used.
- [ ] Small logical commits made.
- [ ] `git diff` reviewed — no unrelated changes, no debug code, no secrets.
- [ ] Documentation updated if behavior changed.
- [ ] No business logic in UI.
- [ ] No duplicated logic.
- [ ] Tests run if they exist.
- [ ] Current branch pushed before switching.
