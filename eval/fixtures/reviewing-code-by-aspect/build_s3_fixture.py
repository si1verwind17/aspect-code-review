#!/usr/bin/env python3
"""Scenario-3 fixture: a hand-authored ledger for a fictional billing service.

Writes base-s3/ beside this file (gitignored): a git repo whose only tracked
file is docs/review/review.md, committed clean with a fixed date. The ledger
follows template/review.md: 16 aspects (the 15 catalog aspects plus the custom
DOC, last), 16 open finding IDs, scores in all three bands, a two-row History,
one archived finding, one credited-as-intentional entry. PAT 8.5 and RDB 7.5
were authored under the earlier count-deducting minor arithmetic and are kept:
the scenario tests parsing, and the renderer never recomputes scores.
Stdlib only.
"""
import os
import shutil
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent / "base-s3"

LEDGER = """\
# Code Review Ledger

Method: aspect-scored review — severity sets the band, count refines within
it; scores derive from open findings by fixed arithmetic. This document is
the persistent ledger: scope, assumptions, overrides, open findings, archive,
history. Finding IDs are stable and never reused. Keep the section names and
order of this template — incremental reviews and future maintainers navigate
by them.

## Summary — 2026-09-30 @ 9c41e7a (incremental review, 16 aspects, scope: diff since 3f0b2d8)

**Worst aspects: Security (SEC) and Logging (LGG) at 3/10.** Open criticals:
- SEC-001 C: the invoice export endpoint serves any tenant's invoices to any API key.
- LGG-001 C: card numbers are written to the request log on every declined charge.

This review resolved ERR-003 C (the retry loop around capture). One finding
was found: TSQ-003. Average (trend only) moved from 6.9 to 7.3.

| Aspect | Score | Worst open | Open findings |
|---|---|---|---|
| Logic correctness (LOG) | **6** | major | LOG-001 M |
| Error handling (ERR) | **5** | major | ERR-001 M, ERR-002 M |
| Security (SEC) | **3** | critical | SEC-001 C |
| Code pattern (PAT) | **8.5** | minor | PAT-001 m, PAT-002 m |
| Concurrency safety (CON) | **10** | none | — |
| Contract & compatibility (CMP) | **9** | minor | CMP-001 m |
| Logging (LGG) | **3** | critical | LGG-001 C |
| Memory (MEM) | **10** | none | — |
| CPU (CPU) | **6** | major | CPU-001 M |
| State discipline (STA) | **10** | none | — |
| Testable code (TST) | **10** | none | — |
| Test quality (TSQ) | **4** | major | TSQ-001 M, TSQ-002 M, TSQ-003 M |
| Type & null safety (TYP) | **9** | minor | TYP-001 m |
| Readability & maintainability (RDB) | **7.5** | minor | RDB-001 m, RDB-002 m |
| Format consistency (FMT) | **10** | none | — |
| API documentation (DOC) | **6** | major | DOC-001 M |

Rows stay in catalog order (the History table's column order), never sorted
by score — so any two reviews line up row-for-row. The worst aspects are
named in the prose above, not by reordering the table.

Average (trend only, never the headline): **7.3**.

## Review scope

Incremental review at 9c41e7a (clean tree): the diff since 3f0b2d8 for all
16 aspects. Findings outside the diff are carried forward from the full
review at 3f0b2d8, which covered `billing/`, `api/`, `tests/` and
`migrations/`.

Context: declared from code.

## Declared assumptions (scout pass @ 3f0b2d8, 2026-09-12)

- **Language(s)**: Python 3.12 (FastAPI), about 2.4k lines; SQL migrations.
- **House pattern standard**: repo-declared (README "Layout"): routers in
  `api/`, services in `billing/`, repositories as module-level functions.
- **Auth model**: in-code. API keys resolved to a tenant by middleware.
- **Deployment model**: assumed 3 replicas behind a load balancer; basis:
  the repo ships k8s manifests (capability evidence only).
- **Custom aspect**: API documentation (DOC), ladder drafted at the full
  review: an undocumented breaking field → major; a stale example → minor.

## User overrides

_None yet._

## Open findings

Severity: C = critical, M = major, m = minor; (w) = widespread (counts
double). Findings open @ 9c41e7a. A finding body stays pinned to its
discovery hash: 3f0b2d8 unless its Status line says `found @<hash>`.

---

### Logic correctness (LOG) — 6/10 · 1 open

**LOG-001 · M · isolated — Proration rounds each line before summing, so multi-line invoices drift by a cent**
- `billing/proration.py:41-58`
- Worksheet: reach any invoice with three or more prorated lines · residue request · signal none → major

---

### Error handling (ERR) — 5/10 · 2 open

**ERR-001 · M · isolated — A webhook signature failure is answered 500 instead of 400**
- `api/webhooks.py:22-30`
- Worksheet: reach the payment provider's webhook · residue request · signal caller → major

**ERR-002 · M · isolated — The dunning job stops at the first failed tenant**
- `billing/dunning.py:64-80`
- Worksheet: reach the nightly dunning run · residue request (later tenants are skipped until the next night) · signal operator → major

---

### Security (SEC) — 3/10 · 1 open

**SEC-001 · C · isolated — Invoice export serves any tenant's invoices to any API key**
- `api/exports.py:18-35` → `billing/invoices.py:102` (no tenant filter)
- Worksheet: reach any API key holder · residue external (another tenant's invoices disclosed) · signal none → critical

---

### Code pattern (PAT) — 8.5/10 · 2 open

**PAT-001 · m · isolated — One repository is a class, against the module-level house pattern**
- `billing/credit_repo.py:1-40`

**PAT-002 · m · isolated — A router computes tax inline instead of calling the service**
- `api/quotes.py:51-60`

---

### Concurrency safety (CON) — 10/10 · 0 open

---

### Contract & compatibility (CMP) — 9/10 · 1 open

**CMP-001 · m · isolated — `/v1/quotes` returns `amount` as a string in one branch and a number in the other**
- `api/quotes.py:72`, `:88`

---

### Logging (LGG) — 3/10 · 1 open

**LGG-001 · C · isolated — Card numbers are written to the request log on declined charges**
- `billing/charges.py:90-97` logs the provider's raw error, which echoes the PAN
- Worksheet: reach every declined charge · residue external (PAN in log storage) · signal none → critical

---

### Memory (MEM) — 10/10 · 0 open

---

### CPU (CPU) — 6/10 · 1 open

**CPU-001 · M · isolated — Invoice listing loads every line item for every invoice on the page**
- `billing/invoices.py:140-171` (N+1 queries)
- Worksheet: reach every invoice list call · residue request (multi-second responses for large tenants) · signal none → major

---

### State discipline (STA) — 10/10 · 0 open

---

### Testable code (TST) — 10/10 · 0 open

---

### Test quality (TSQ) — 4/10 · 3 open

**TSQ-001 · M · isolated — Proration tests assert only that a total exists**
- `tests/test_proration.py:12-40`. Mutation: round half-down → green.
- Worksheet: reach every proration · residue request · signal none → major

**TSQ-002 · M · isolated — The webhook tests never send a bad signature**
- `tests/test_webhooks.py`. Mutation: skip verification → green.
- Worksheet: reach the webhook · residue external · signal none → major

**TSQ-003 · M · isolated — The capture retry fix has no test**
- Status: open, found @9c41e7a
- `billing/capture.py:30-52`. Mutation: retry on any error again → green.
- Worksheet: reach every capture · residue external (a double charge) · signal none → major

---

### Type & null safety (TYP) — 9/10 · 1 open

**TYP-001 · m · isolated — `Invoice.paid_at` is typed `datetime` but is None until paid**
- `billing/models.py:33`

---

### Readability & maintainability (RDB) — 7.5/10 · 2 open

**RDB-001 · m · isolated — Three helpers named `calc` in one module**
- `billing/tax.py:10`, `:44`, `:81`

**RDB-002 · m · isolated — Magic number 86400 for the grace period**
- `billing/dunning.py:12`

---

### Format consistency (FMT) — 10/10 · 0 open

---

### API documentation (DOC) — 6/10 · 1 open

**DOC-001 · M · isolated — The OpenAPI schema omits the `currency` field added to invoices**
- `api/schemas.py:20-48`; `openapi.yaml:310`
- Worksheet: reach every API client generated from the schema · residue request · signal none → major

## Credited as intentional (recorded to prevent re-litigation)

- Webhook handlers acknowledge before processing; the provider retries and
  the handler is idempotent on event id (`api/webhooks.py:40-55`).

## Resolved findings (archive)

One line per resolved finding — `<ID> · <C|M|m> · <title> · <files> ·
resolved @<hash>`; full bodies live in this document's git history. A
reintroduced defect reopens its ID here (moves back to Open findings with
`reopened @<hash>`), never gets a new one.

- ERR-003 · C · Capture is retried on a timeout, so a slow provider double-charges · `billing/capture.py` · resolved @9c41e7a

## History

| Date | Hash | LOG | ERR | SEC | PAT | CON | CMP | LGG | MEM | CPU | STA | TST | TSQ | TYP | RDB | FMT | DOC | Worst | Avg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-12 | 3f0b2d8 | 6 | 3 | 3 | 8.5 | 10 | 9 | 3 | 10 | 6 | 10 | 10 | 5 | 9 | 7.5 | 10 | 6 | ERR, SEC, LGG (3) | 6.9 |
| 2026-09-30 | 9c41e7a | 6 | 5 | 3 | 8.5 | 10 | 9 | 3 | 10 | 6 | 10 | 10 | 4 | 9 | 7.5 | 10 | 6 | SEC, LGG (3) | 7.3 |

Per-aspect baselines (diff basis for the next incremental review): all 16
aspects @ 9c41e7a, whole repo.
"""


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "docs" / "review").mkdir(parents=True)
    (OUT / "docs" / "review" / "review.md").write_text(LEDGER)
    env = dict(os.environ, GIT_AUTHOR_DATE="2026-09-30T12:00:00Z", GIT_COMMITTER_DATE="2026-09-30T12:00:00Z",
               GIT_AUTHOR_NAME="fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
               GIT_COMMITTER_NAME="fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
    run = lambda *a: subprocess.run(a, cwd=OUT, env=env, check=True, capture_output=True)
    run("git", "init", "-q", "-b", "main")
    run("git", "add", "-A")
    run("git", "commit", "-q", "-m", "billing-service review ledger")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
