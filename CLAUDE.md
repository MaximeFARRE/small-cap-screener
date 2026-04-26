# CLAUDE.md

Read `AGENTS.md` and `STACK.md` before any change.

## Workflow

1. `git branch` — never work on `main`.
2. Branch: `feat/`, `fix/`, `docs/`, `chore/`, `test/`.
3. Read existing files before editing.
4. Smallest possible change. No unrelated edits.
5. Commit after each logical step.
6. `git diff` before finishing.

## Architecture

```
UI → Services → Repository / DB
```

- UI = display and interaction only.
- Services = all business logic.
- Repositories = all DB / API access.
- Never cross layers. Never duplicate logic.

## Code quality

- Explicit types and annotations. No magic values — use named constants.
- No `except: pass`, no empty catch blocks, no silent failures.
- No `print()` / `console.log()` in committed code.
- One responsibility per function. Explicit names. Functions ≤ 40 lines.
- Validate only at system boundaries (user input, external APIs).
- No hardcoded credentials. No TODO/FIXME in committed code.
- If ambiguous, state assumptions before coding.

## Commits

`feat|fix|docs|chore|test: <what and why>`
One logical change = one commit. Never batch unrelated changes.

## Before finishing

- [ ] Tests pass (if they exist).
- [ ] `git diff` reviewed — no unrelated changes, no debug code, no secrets.
- [ ] Documentation updated if behavior changed.
