# Data Normalization Conventions

This document defines the internal format expected after normalization.

## Pipeline Order

```text
fetch -> normalize -> validate -> store
```

No provider payload should be stored directly.

## Ticker Convention

- Stored as uppercase string.
- Leading and trailing spaces are removed.
- Example: `" tte.pa "` -> `"TTE.PA"`.

## ISIN Convention

- Stored as uppercase string when present.
- Expected format: `^[A-Z]{2}[A-Z0-9]{10}$`.
- Missing ISIN is allowed as warning.
- Invalid format is blocking.

## Currency Convention

- Internal format uses ISO-like 3-letter uppercase code.
- Aliases are normalized when possible:
  - `EURO` / `EUROS` -> `EUR`
  - `US DOLLAR` / `US DOLLARS` -> `USD`
- Inconsistent currencies across sources are blocking.

## Date Convention

- Internal type is calendar `date` (no timezone in stored values).
- Accepted input: `date`, `datetime`, or ISO string.
- Timezone-aware datetimes are converted to UTC date before storage.
