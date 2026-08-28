# Decisions

Running log of design decisions with the reasoning captured at the time.
Format loosely follows ADR: **Context → Decision → Consequences**.

---

## 2026-08-27 — DB driver: sync `psycopg`, not `asyncpg`

**Context.** `requirements.txt` originally listed both `asyncpg` and
`psycopg[binary]`, but nothing was consistently wired: the alembic URL
uses `postgresql+psycopg://…`, `app/db/session.py` uses `create_engine`
(sync), `/health` is a `def` endpoint, and every test is sync. `asyncpg`
was installed but never imported.

**Decision.** Standardize on sync `psycopg` (v3). Remove `asyncpg` from
`requirements.txt` and uninstall it from the environments.

**Why.**
- The whole stack is already sync — matching it removes the cognitive
  overhead of maintaining two DB access styles.
- FastAPI runs sync (`def`) endpoints in a threadpool, so sync drivers
  don't block the event loop. Fine for a URL shortener's I/O-light
  request pattern.
- Alembic is naturally sync — a sync app driver keeps one URL format
  and one connection story end-to-end.
- `pool_pre_ping=True` on the sync engine covers the main real-world
  concern (stale connections after DB restarts).

**Consequences.**
- Concurrency ceiling is bounded by the threadpool, not the event loop.
  Acceptable for expected load; if we ever need >1k concurrent DB-bound
  requests per instance, revisit with `asyncpg` + `AsyncSession`.
- No `async def` endpoints that touch the DB — use `def` and depend on
  `get_db()`. If we add async endpoints for non-DB work (e.g. calling
  external APIs), that's still fine; they just can't share the session.
- Any future switch to async is a non-trivial migration
  (engine, sessionmaker, dependency, and every endpoint change).

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

---

## 2026-08-28 — Redirect with 302 Found (not 301)

**Context.** `GET /{code}` resolves a short code to its original URL and
issues an HTTP redirect. The two realistic choices are `301 Moved
Permanently` (browsers and intermediaries cache the redirect
aggressively — often indefinitely) and `302 Found` (treated as
non-cacheable by default, so each click round-trips to the shortener).
`307`/`308` are the method-preserving variants and behave the same as
`302`/`301` respectively for a GET-only lookup.

**Decision.** Return **`302 Found`**.

**Why — Day-4 trade-off, named explicitly.** Day 4 is when click
analytics land. Analytics only work if every click actually hits this
service; `301` would let browsers and CDNs short-circuit the shortener
after the first hit, and those repeat clicks would never be observed
or countable. `302` costs us a shortener round-trip per click (no edge
caching, the app must stay hot and reachable) and buys us:
- **Countable clicks** on Day 4 without changing the redirect contract.
- **Live target changes**: editing `original_url` takes effect on the
  next click, instead of being masked by stale browser/CDN caches for
  users who've already seen the link.
- **Reversible expiry**: an expired link that gets un-expired starts
  working again immediately, rather than being cached as gone.

**Consequences.**
- Every click is a request the shortener must serve — capacity planning
  and uptime matter more than they would with `301`.
- No SEO / link-equity benefit that `301` would confer (irrelevant for
  a shortener; the destination is the canonical URL).
- If we ever decide analytics aren't worth the load, switching to `301`
  is a one-line change — but any URLs already served as `302` won't
  have been cached, so the cutover is clean in one direction only
  (302 → 301 is easy; 301 → 302 is not, because the 301s are already
  cached in the wild).

---

## 2026-08-28 — Expired links return 410 Gone (not 404)

**Context.** `urls.expires_at` is nullable; NULL means permanent. On
`GET /{code}`, if the row exists but `expires_at <= now()`, we have to
choose how to signal that to the client. The two reasonable options are
a plain `404 Not Found` (treat expired as "no such link") or a distinct
`410 Gone` (the code existed but is intentionally no longer available).

**Decision.** Return **`410 Gone`** for expired links. `404 Not Found`
is reserved for "no row with this short_code."

**Why.**
- Truthful signal: `410` means "was here, deliberately gone" — which is
  exactly what expiry is. Conflating it with `404` loses that info.
- Cache/crawler friendliness: `410` tells search engines and
  intermediary caches to drop the URL more aggressively than `404`,
  which they may treat as transient.
- Cheap to distinguish for callers: any client that already handles
  `404` can add a `410` branch trivially; those that don't will still
  fail closed (both are 4xx).

**Consequences.**
- Two distinct 4xx codes for the "can't redirect" case — clients that
  want a single "gone-or-missing" bucket must OR them together.
- Expired rows are still returned by the DB lookup; the endpoint bears
  the responsibility of checking `expires_at`. A future background
  sweep that hard-deletes expired rows would silently convert `410`s
  into `404`s.
