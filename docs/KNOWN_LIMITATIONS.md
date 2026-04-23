# KNOWN_LIMITATIONS.md

# Known Limitations

This file documents the current limitations of the project.

The goal is to be transparent about what is unfinished, simplified, or intentionally excluded.

Documenting limitations makes the repository look more professional and helps future contributors understand the current state of the project.

---

## Typical Limitations

Replace or remove the examples below depending on the project.

### Performance

- Large datasets may be slow to load
- No caching is currently implemented
- Some operations are synchronous and may block the UI

### Error Handling

- Error handling is incomplete in some areas
- Network or database failures may not always be displayed clearly
- Validation is currently limited to basic cases

### Tests

- Test coverage is incomplete
- Only critical paths are tested
- Edge cases are not fully covered yet

### User Interface

- The UI is optimized for desktop only
- Mobile responsiveness may be incomplete
- Accessibility has not been fully tested

### Data / Persistence

- The database schema may still evolve
- Migration support may not exist yet
- Imported data is not always validated perfectly

### Security

- Authentication may be basic or incomplete
- Rate limiting may not exist
- Secrets management may still rely on local `.env` files

---

## Technical Debt

List technical debt explicitly instead of hiding it.

Example:

```text id="aq2a0r"
- Some validation logic still exists in the UI and should be moved to services
- Several large files should eventually be split into smaller modules
- Duplicate code exists in the import workflow
````

---

## Deliberate Non-Goals

It is acceptable for a project not to include everything.

Examples:

```text id="hh6w0s"
- No multi-user support
- No production deployment yet
- No offline mode
- No advanced authentication
```

---

## Future Improvements

See `docs/ROADMAP.md` for planned improvements and future work.

```
```
