# CODEX.md — Codex Operating Instructions

See `AGENTS.md` and `STACK.md` for the full operating manual.

---

## Git setup (Codex-specific)

If git returns a "dubious ownership" or permission error inside a Codex sandbox, run once:

```bash
git config --global --add safe.directory '*'
```

Or add to `~/.codex/config.toml`:

```toml
setup_commands = ["git config --global --add safe.directory '*'"]
```
