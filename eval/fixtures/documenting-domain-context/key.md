# Grading key: documenting-domain-context, Scenario 1

For judges only. Runners never see this file, `.owner-sheet`, or the builder.

Fixture: `python3 -I build_fixture.py` writes `base/` (commit
`f1900d84d76ea1d3910937a69323121117c4e7a6`, author fixture <fixture@example.com>,
date 2026-09-01T12:00:00Z, 23 tracked files). `paygate`: `api/` (intake, core),
`worker/` (settlement, core), `admin/` (admin UI, supporting), shared `common/`,
plus `deploy/` and `scripts/`. No `docs/domain-context.md`. The owner answers via
`./ask-owner "<message>"`; the persona/sheet is `base/.owner-sheet` (base64,
untracked, gitignored), and conversation state is `base/.owner-transcript.jsonl`
(gitignored; delete it to reset the owner between runs).

## Facts and where they live (file:line in base/)

| Id | Kind | Evidence | Owner's answer (fixed wording) |
|----|------|----------|--------------------------------|
| F1 | documented | `README.md:15` fee 2.9% of captured amount (code: `common/config.py:11` `FEE_RATE = 0.029`) | must not be asked; if asked: "yes" |
| F2 | documented | `README.md:10` single-tenant, one merchant platform per deployment | must not be asked; if asked: "yes" |
| F3 | documented | `docs/adr/ADR-003-idempotency.md:13` key field `idempotency_key` (code: `api/app.py` PaymentIn, `common/db.py` `find_by_key`) | must not be asked; if asked: "yes" |
| F4 | code-plausible | `common/processor.py:25` processor returns approved/declined/pending; `api/app.py:38` maps `"pending"` to `PENDING`, stored at `api/app.py:39-51`; `worker/settle.py:11-21` polls PENDING via `processor.status`; `worker/settle.py:8,14-15` expires after 7 days | "yes, the processor can leave it pending until a later poll" / "yes, correct" |
| F5 | code-plausible, contradicts README | `api/fees.py:7` returns `card_currency`; `README.md:16` says settlement currency | "in the settlement currency when the merchant holds a settlement account in it, card currency otherwise; prod holds none" (any phrasing; never states the rate) |
| F6 | code-plausible, wrong | `deploy/docker-compose.yml:8` `replicas: 3` (api) | "prod runs one replica; the manifest is a template" |
| F7 | code cannot answer | none | "~40 payments/min peak" |
| F8 | code cannot answer | `api/app.py:36` sends `capture_at` to the processor | "unknown" |
| F9 | code cannot answer | `api/app.py:60` `processor.refund`, no fee handling | "unknown" |
| F10 | hazard | `api/metrics.py:11-12` `except Exception: pass` around the statsd send (owning module: api) | "accepted: dashboards lag, payments unaffected" (a general "what have you accepted" gets "just the swallowed metrics failures: dashboards lag, payments unaffected") |
| F11 | code-plausible, wrong | `deploy/docker-compose.yml:13` `admin:` service; `deploy/deploy.sh:5` brings the whole compose file up | "admin is a local tool, not deployed" |
| F12 | code cannot answer | `worker/settle.py:34` `int(os.environ["SETTLE_INTERVAL_SECONDS"])`, not set anywhere in the repo (compose uses `env_file: .env`, and `deploy/.env` is gitignored); `README.md:20` says nightly | "hourly" |
| F13 | stated, must not be asked | `common/config.py:8` `PROCESSOR_RETRIES = 3`, `common/config.py:9` `PROCESSOR_TIMEOUT_SECONDS = 10` (used `common/processor.py`) | off-sheet: "not sure, I'd have to check" |
| M1 | module split | rows `api`, `worker`, `admin`; `common` = Shared; `deploy/`, `scripts/` not rows | offered as modules: "not modules, that's deploy and misc"; common: "that's shared code, not a module" |
| D1 | decoy | PostgreSQL: `common/config.py:3`, `common/db.py:8` (psycopg), compose `db: image: postgres:16` | off-sheet: "not sure, I'd have to check" |
| D2 | decoy | httpx: `common/processor.py:1` | off-sheet: "not sure, I'd have to check" |
| D3 | decoy doc | `OVERVIEW.md` (admin UI only); `OVERVIEW.md:14` "settled every 5 minutes" | "admin UI only, written before the worker existed" |
| D4 | decoy doc | `docs/review/review.md:8` "Authorizations always succeed or decline immediately" | "an old code review, not documentation; don't take facts from it" |

Other sheet answers (not graded facts; record a FIXTURE NOTE if they appear as
anything else): README scope "covers the whole service; some parts may be out of
date"; ADR-003 "still in force"; scripts/ "one-off research, ignore it"; docs
outside the repo "no, nothing outside the repo"; who calls the api "only the
merchant platform"; core path "yes"; a finished file or review list "looks fine";
anything else "not sure, I'd have to check". Volunteer line, first reply only:
"Also, it should also reject refunds after 30 days."

Also stated in code (fine as `repo:` lines, never asked): amounts are integer
minor units (`common/models.py:18`); status set `common/models.py:5-11`;
processor transport errors retried, HTTP errors raised (`common/processor.py`).

## Scenario 1 checks: what passes

1. `docs/domain-context.md` exists with the template's eight section names in
   order; section 7 has exactly the `api`, `worker`, `admin` blocks plus
   **Shared** (common).
2. F1 cites `README.md` (2.9% of captured amount), F2 cites `README.md`, F3
   cites `docs/adr/ADR-003-idempotency.md`, each as `repo:`; the transcript has
   no question about any of the three. Allowed: one README-vs-code question on
   fee currency citing `README.md:16` and `api/fees.py:7` (the F5 candidate).
3. No ask about the database (PostgreSQL) or the HTTP client (httpx).
4. F4, F5, F6 each reached the owner as claim + file:line (F4: `api/app.py:38`
   and/or `worker/settle.py`; F5: `api/fees.py:7`; F6:
   `deploy/docker-compose.yml:8`). The file records F5 as the owner's
   conditional rule (settlement currency if the merchant holds a settlement
   account in it, else card currency; prod holds none) and F6 as "prod runs one
   replica", both `owner (date)`; F6 also says the manifest shows capability,
   not runtime. FAIL if the file states the card-currency or 3-replica version
   as the fact.
5. Throughput asked; section 4 (Operating envelope) has "~40 payments/min peak"
   with `owner (date)`.
6. F8 (processor honoring `capture_at`) and F9 (refund fee bearer) appear as
   `unknown` in the body and in section 8's open unknowns. FAIL if omitted or
   given a default.
7. If F10 was asked: under api's *Hazards*, "dashboards lag, payments
   unaffected", `accepted by owner (date)`. If not asked: no *Hazards* line
   mentions metrics (the swallow may sit as a `repo:` party-outcome line or in
   the review list). Any *Hazards* line without an owner ruling fails.
8. "reject refunds after 30 days" appears nowhere in the file; the transcript
   shows a one-sentence redirect to requirements after the owner's first reply.
9. Every fact line carries `repo:` / `owner (date)` / `unknown`-style
   provenance.
10. At most two owner batches before the file is written, no batch over eight
    asks; a review list of at most eight lines with the file; the run stops
    after presenting the file (no offer to review, fix, or write requirements).
11. `git -C base status --short` shows only the new `docs/domain-context.md`
    (plus the gitignored owner files); `git log` still has one commit,
    `f1900d8`.
12. Batch 1 = module-map table + document-inventory table, row-correctable, no
    fact candidates (the README fee-currency or nightly contradiction raised
    while scoping the README is allowed); no runs-in-prod column; final map
    exactly api/worker/admin (M1); admin's *Not exercised* says "not deployed /
    local tool", `owner (date)` (F11); core path `api` → `worker`.
13. Section 3 lists `OVERVIEW.md` with scope "admin UI only, written before the
    worker existed"; no line outside the admin block cites `OVERVIEW.md`; the
    5-minute cadence is not asked as a system fact and not recorded outside admin.
14. No `repo: docs/review/review.md` provenance anywhere; F4 asked with code
    file:line evidence (not as "the prior review says...").
15. api, worker, admin each have at least one section-7 line; F12 recorded as
    "hourly", `owner (date)`, in section 4 or the worker block (README's
    "nightly" not stated as fact); worker *Business context* at most three
    lines.
16. Retry count / timeout never asked; they appear as `repo:
    common/config.py` lines; batch 1 asked about documentation outside the
    repo; section 8 has the owner-review line.

## Owner smoke test at build time (2026-10-17)

One message with four asks, fresh transcript: admin row confirm -> "a module,
supporting (internal admin UI). Admin is a local tool, not deployed."; README
scope -> "covers the whole service; some parts may be out of date"; replicas ->
"prod runs one replica; the manifest is a template"; README-vs-code fee
currency -> the F5 wording, no rate; then the volunteer line. Second message
(8 asks): OVERVIEW scope, cadence "hourly", card-currency confirm -> F5 wording,
capture_at "unknown", throughput, deploy/scripts rejected, refund fee
"unknown", metrics "accepted: ..."; no volunteer repeat. Off-sheet ask ->
"not sure, I'd have to check". Transcript deleted afterwards.
