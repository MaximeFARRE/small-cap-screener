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

## Financial Fields Convention

- Internal statement fields use one stable naming set:
  - `revenue`
  - `ebitda`
  - `ebit`
  - `net_income`
  - `free_cash_flow`
  - `total_assets`
  - `total_equity`
  - `total_debt`
  - `net_debt`
  - `shares_outstanding`
- Fiscal date is derived from normalized statement metadata:
  - `annual` -> `YYYY-12-31`
  - `half_year` -> `YYYY-06-30`

## `None` Handling Rules

- `None` is accepted for optional fields and kept as `None`.
- Missing critical identifiers (`ticker`) are blocking.
- Missing optional data (for example ISIN or currency) generates warnings.
- Invalid numeric values (non-finite, negative where forbidden) are blocking.

## Deduplication Rules

- Deduplication is performed after date normalization.
- `price_history` is deduplicated by `date`.
- `dividends` is deduplicated by `ex_date`.
- `splits` is deduplicated by `split_date`.
- On duplicate keys, the latest normalized record in the input sequence is kept.
- Every dedup event emits a warning.
