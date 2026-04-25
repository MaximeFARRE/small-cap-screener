# Release Process

This project uses `python-semantic-release` with Conventional Commits.

## Rules

- Commit messages must follow: `feat|fix|docs|chore|test|refactor: short description`
- Release automation runs only on `main`
- Tag format is `vX.Y.Z`

## Automated flow

On each push to `main`, `.github/workflows/release.yml` runs:

1. detect the next version from commit history
2. update `project.version` in `pyproject.toml`
3. update `CHANGELOG.md`
4. create a release commit and tag
5. publish a GitHub release

## Local dry run

Use no-op mode before merging:

```bash
python -m semantic_release --noop version --print
python -m semantic_release --noop changelog
```

## Notes

- Feature work should happen on feature branches.
- The release commit and tag are created by GitHub Actions on `main`.
