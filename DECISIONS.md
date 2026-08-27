# Decisions

Running log of design decisions with the reasoning captured at the time.
Format loosely follows ADR: **Context → Decision → Consequences**.

---

## 2026-08-27 — Base62 encoding: own module, no library

**Context.** URL shortening needs a compact, URL-safe encoding of the row's
integer id. Options considered: `pyshorteners`, `short-uuid`,
`python-baseconv`, or a hand-written `app/services/base62.py`.

**Decision.** Hand-written module at `app/services/base62.py`.
Alphabet: `0-9a-zA-Z` (digits, lowercase, uppercase — in that order).

**Why.**
- Zero external dependency for a ~20-line, well-understood algorithm.
- Full control over the alphabet and error handling — libraries often
  bundle extra behavior (e.g. random padding, url-safety tweaks) we don't
  want.
- Trivial to unit-test end-to-end (see `tests/test_base62.py`, 20 tests).

**Consequences.**
- Must maintain it ourselves (small burden).
- Changing the alphabet later is a breaking change for existing short
  codes — the alphabet is part of the URL contract.
- Alphabet order is fixed at `0-9a-zA-Z`; if we ever want
  case-insensitive short codes we'll need a new decision.

---

## 2026-08-27 — URL model shape

**Context.** Need a schema that maps stored URLs to short codes and
supports optional expiry.

**Decision.** `app/models/url.py` defines:

| column         | type                        | notes                             |
|----------------|-----------------------------|-----------------------------------|
| `id`           | `BigInteger`, PK, autoinc   | internal surrogate key            |
| `short_code`   | `String(16)`, unique, NN    | stored, not derived on read       |
| `original_url` | `Text`, NN                  | unbounded length                  |
| `created_at`   | `DateTime(tz=True)`, NN     | timezone-aware                    |
| `expires_at`   | `DateTime(tz=True)`, null   | NULL = permanent link             |

**Why.**
- **`id` decoupled from `short_code`.** `id` is an internal surrogate;
  `short_code` is stored (not computed at read time) so the encoding
  scheme (base62 today) can evolve without breaking existing links.
- **`BigInteger` id.** Headroom for growth; base62-encoded 64-bit ints
  fit comfortably in 11 chars.
- **`short_code` unique + length 16.** Enforces the URL contract at the
  DB layer and leaves margin above the ~11 chars a 64-bit id needs.
- **`original_url` as `Text`.** URLs have no reliable upper bound.
- **Timezone-aware timestamps.** Avoids the classic naive-vs-aware
  ambiguity; UTC everywhere.
- **`expires_at` nullable.** NULL sentinel for permanent links keeps the
  common case free of magic dates.

**Consequences.**
- Two write paths must stay in sync: on insert, compute `short_code =
  base62.encode(id)` after the id is assigned (or reserve id first).
- Any future encoding change requires a migration strategy for existing
  rows (backfill or dual-read).
- No index on `original_url` — dedup-by-URL would require adding one.
