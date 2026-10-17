# Fixture: reviewing-code-by-aspect

Shared by every review scenario. The seed, decoy and plant lists are the answer key: judges grade against them, never against their own review taste.

Fixture: a small synthetic service (~10 files, one language, e.g. Python
FastAPI or Go) generated fresh per run into a temp git repo, with **seeded
defects** and **seeded decoys** (correct code that a naive reviewer flags).
The seed list below is the answer key; graders score against it, not against
their own review taste.

Builder: [`eval/fixtures/reviewing-code-by-aspect/build_fixture.py`](../../fixtures/reviewing-code-by-aspect/build_fixture.py)
writes the scenario-1 fixture, dirty-tree edit included, to `base/` beside
itself (gitignored); copy it into the run's temp directory.
[`build_s2_fixture.py`](../../fixtures/reviewing-code-by-aspect/build_s2_fixture.py) writes the
scenario-2 fixture (stdlib only, fixed commit dates so hashes are stable) to `base-s2/`, with
the commit hashes in `base-s2-hashes.json`.
[`build_s3_fixture.py`](../../fixtures/reviewing-code-by-aspect/build_s3_fixture.py) writes the
scenario-3 ledger repo to `base-s3/`; its grading key is in the scenario file.

Seeded defects (each maps to an aspect and expected tier):

1. `except Exception: pass` around a DB write mid-mutation — ERR critical.
2. Retry loop around a non-idempotent payment call — ERR critical.
3. f-string interpolation of a request param into SQL — SEC critical.
4. `GET /orders/{id}` fetches without ownership check (auth via header set
   by upstream proxy; manifests present) — SEC critical (IDOR survives the
   perimeter model).
5. Module-level dict cache keyed by user id, no eviction — MEM critical.
6. Two modules use camelCase functions, the rest snake_case — FMT minor
   (one finding with an occurrence list, never per-file findings).
7. Inverted condition: discount applied when `total < threshold` should be
   `>=` — LOG critical or major (silent wrong pricing).
8. A test file whose assertions are all `assert True` — TSQ major.

Seeded decoys (flagging any is a check FAILURE):

D1. O(n²) loop over a ≤20-element config list on startup — CPU suppression
    (no scale, cold path).
D2. Missing in-code authn middleware — suppressed under the declared
    perimeter model (sidecar manifests in repo).
D3. MD5 used for a cache key — non-security use.
D4. A documented best-effort swallow: `# fire-and-forget metrics, failure ok`.
D5. Repository class containing raw SQL "untestable without a DB" — TST
    suppression. A decoy hit is the "needs an interface / untestable"
    claim; an idiom-consistency minor on the same class (house uses
    module-level functions) is a legitimate PAT observation, not a hit.
