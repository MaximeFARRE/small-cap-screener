# Release Process

This repository uses `python-semantic-release` with Conventional Commits.

## Release source

- releases are generated from `main`
- tags use `vX.Y.Z`
- version source is `pyproject.toml` (`project.version`)

## Commit types and version bump

- `fix:` -> patch
- `feat:` -> minor
- `type!:` or `BREAKING CHANGE:` footer -> major

Examples:

```text
feat: add screener snapshot comparison endpoint
fix: prevent stale ticker cache on refresh
docs!: align documentation with v2 architecture
```

With footer:

```text
docs: align release docs

BREAKING CHANGE: release baseline now targets v2 architecture.
```

## Automated flow

On push to `main`, release workflow should:

1. detect next semantic version from commits
2. update `pyproject.toml` version
3. update `CHANGELOG.md`
4. create release commit and tag
5. publish GitHub release

## Local dry run

```bash
python -m semantic_release --noop version --print
python -m semantic_release --noop changelog
```

## Notes

- do release prep work on feature/docs branches
- merge to `main` with clean commit history
- avoid mixing unrelated changes in release-triggering commits
