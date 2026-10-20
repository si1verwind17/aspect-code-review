#!/usr/bin/env python3
"""Scenario-1 fixture for fixing-reviewed-findings: a stock-reservation
service with a reviewed ledger.

Writes base/ beside this file (gitignored): a git repo on `main` with two
commits at fixed dates — the code, then its full review ledger — so hashes
are stable. The ledger holds four open findings: the target LOG-001, CON-001
whose cited lines overlap the target's (no ID cross-ref between them) but
whose race sits on a line the target's fix does not need to touch, and
two unlinked findings, LOG-002 (same file, another function) and CMP-001
(docs). Fixing LOG-001 properly needs a new error and HTTP status. The tests
run with `python3 -m unittest`. Stdlib only.
"""
import os
import shutil
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent / "base"

RESERVATIONS = '''\
"""Stock reservations with client idempotency keys.

The server runs each request on its own thread (ThreadingHTTPServer), so
stock levels are only read and written under _lock.
"""
import threading
import uuid

from stockroom import store


class OutOfStock(Exception):
    pass


class UnknownReservation(Exception):
    pass


_lock = threading.Lock()
_reservations = {}  # reservation id -> reservation
_by_key = {}  # idempotency key -> reservation id


def reserve(sku, qty, key):
    """Hold qty of sku. A repeated key returns the reservation it created."""
    with _lock:
        existing = _by_key.get(key)
        if existing is not None:
            return _reservations[existing]
        if store.available(sku) < qty:
            raise OutOfStock(sku)
        store.take(sku, qty)
        rid = uuid.uuid4().hex
        _reservations[rid] = {"id": rid, "sku": sku, "qty": qty, "state": "held"}
    _by_key[key] = rid
    return _reservations[rid]


def release(rid):
    """Return a held reservation's stock."""
    with _lock:
        r = _reservations.get(rid)
        if r is None:
            raise UnknownReservation(rid)
        store.put(r["sku"], r["qty"])
        r["state"] = "released"
        return r
'''

STORE = '''\
"""In-memory stock levels. Callers hold reservations._lock."""
_levels = {}


def set_level(sku, qty):
    _levels[sku] = qty


def available(sku):
    return _levels.get(sku, 0)


def take(sku, qty):
    _levels[sku] -= qty


def put(sku, qty):
    _levels[sku] += qty
'''

SERVER = '''\
"""HTTP front: POST /reservations and POST /reservations/<id>/release."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from stockroom import reservations

STATUS = {
    reservations.OutOfStock: 409,
    reservations.UnknownReservation: 404,
}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        try:
            if self.path == "/reservations":
                key = self.headers["Idempotency-Key"]
                result = reservations.reserve(body["sku"], int(body["qty"]), key)
            elif self.path.startswith("/reservations/") and self.path.endswith("/release"):
                result = reservations.release(self.path.split("/")[2])
            else:
                return self._send(404, {"error": "NotFound"})
        except tuple(STATUS) as e:
            return self._send(STATUS[type(e)], {"error": type(e).__name__})
        return self._send(200, result)

    def _send(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    ThreadingHTTPServer(("", 8080), Handler).serve_forever()


if __name__ == "__main__":
    main()
'''

TESTS = '''\
import unittest

from stockroom import reservations, store


class ReservationTest(unittest.TestCase):
    def setUp(self):
        reservations._reservations.clear()
        reservations._by_key.clear()
        store._levels.clear()
        store.set_level("A", 10)

    def test_reserve_takes_stock(self):
        r = reservations.reserve("A", 3, "k1")
        self.assertEqual(r["qty"], 3)
        self.assertEqual(store.available("A"), 7)

    def test_out_of_stock(self):
        with self.assertRaises(reservations.OutOfStock):
            reservations.reserve("A", 11, "k1")

    def test_same_key_replays(self):
        first = reservations.reserve("A", 3, "k1")
        again = reservations.reserve("A", 3, "k1")
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(store.available("A"), 7)

    def test_release_returns_stock(self):
        r = reservations.reserve("A", 3, "k1")
        reservations.release(r["id"])
        self.assertEqual(store.available("A"), 10)


if __name__ == "__main__":
    unittest.main()
'''

API_DOC = '''\
# Stockroom API

## POST /reservations

Header `Idempotency-Key` (required). Body `{"sku": "...", "qty": n}`.
A request repeated with the same key returns the reservation the key created.

200 with the reservation `{id, sku, qty, state}`.

## POST /reservations/{id}/release

Returns the reservation's stock. Answers 204 with no body.

## Errors

Every error body is `{"error": "<name>"}`.

| Status | error | When |
|---|---|---|
| 404 | UnknownReservation | no reservation has that id |
| 404 | NotFound | unknown route |
| 409 | OutOfStock | not enough stock for the request |
'''

README = '''\
# stockroom

Holds stock for an order flow. One process, in-memory state; the order
service retries any request that times out, reusing its Idempotency-Key.

- `stockroom/reservations.py` — reserve and release, idempotency keys
- `stockroom/store.py` — stock levels
- `stockroom/server.py` — HTTP front (`python3 -m stockroom.server`)
- `docs/api.md` — the API contract the order service codes against

Tests: `python3 -m unittest`.
'''


def line_of(src, needle, nth=1):
    hits = [i + 1 for i, l in enumerate(src.splitlines()) if needle in l]
    return hits[nth - 1]


def ledger(h):
    r = RESERVATIONS
    lookup = line_of(r, "existing = _by_key.get(key)")
    replay = line_of(r, "return _reservations[existing]")
    insert = line_of(r, "_by_key[key] = rid")
    rel_from = line_of(r, "def release(rid):")
    rel_put = line_of(r, 'store.put(r["sku"], r["qty"])')
    doc_204 = line_of(API_DOC, "Answers 204")
    srv_200 = line_of(SERVER, "return self._send(200, result)")
    return f"""\
# Code Review Ledger

Method: aspect-scored review — severity sets the band, count refines within
it; scores derive from open findings by fixed arithmetic. This document is
the persistent ledger: scope, assumptions, overrides, open findings, archive,
history. Finding IDs are stable and never reused. Keep the section names and
order of this template — incremental reviews and future maintainers navigate
by them.

## Summary — 2026-10-01 @ {h} (full review, 6 aspects, scope: whole repo)

**Worst aspect: Logic correctness (LOG) at 5/10.** No open criticals.

First review of the repository: four findings, three of them major.

| Aspect | Score | Worst open | Open findings |
|---|---|---|---|
| Logic correctness (LOG) | **5** | major | LOG-001 M, LOG-002 M |
| Error handling (ERR) | **10** | none | — |
| Security (SEC) | **10** | none | — |
| Code pattern (PAT) | **10** | none | — |
| Concurrency safety (CON) | **6** | major | CON-001 M |
| Contract & compatibility (CMP) | **9** | minor | CMP-001 m |

Rows stay in catalog order (the History table's column order), never sorted
by score — so any two reviews line up row-for-row. The worst aspects are
named in the prose above, not by reordering the table.

Average (trend only, never the headline): **8.3**.

## Review scope

Whole repository at {h} (clean tree): `stockroom/`, `tests/`, `docs/`.

Context: declared from code (no owner-confirmed context).

## Declared assumptions (scout pass @ {h}, 2026-10-01)

Evidence-based detections; each states the weakest claim its evidence
supports. Override any of these in User overrides — overrides persist and
bind future reviews.

- **Language(s)**: Python 3 (stdlib only), about 150 lines.
- **House pattern standard**: dominant pattern: module-level functions over
  module state; exceptions mapped to statuses in `server.py`.
- **Auth model**: none in code; assumed behind the order service's network.
- **Deployment model**: one process (README); requests run concurrently on
  ThreadingHTTPServer threads.
- **Consumed contract surfaces**: the HTTP API in `docs/api.md`, consumed by
  the order service, which retries timed-out requests with the same key.
- **Tests**: unittest, `python3 -m unittest`; four tests, all pass.
- **Exclusions**: none.
- **Domain facts**: none beyond the README.
- **Sweeps run**: lock-coverage sweep · `stockroom/` · every read or write
  of `_reservations`, `_by_key` and `store` · one write outside `_lock`
  (CON-001).
- **Scoring interpretation**: none → 10; minors only → 9 flat; within the
  worst open C/M tier each verified finding counts one unit; score = band
  start − step × (units − 1), clamped at the band floor (critical 3/−1/0,
  major 6/−1/4).

## User overrides

_None yet._

## Open findings

Severity: C = critical, M = major, m = minor; (w) = widespread (counts
double). Findings open @ {h}. A finding body stays pinned to its discovery
hash: {h} unless its Status line says `found @<hash>`.

---

### Logic correctness (LOG) — 5/10 · 2 open

**LOG-001 · M · isolated — Idempotency replay ignores the request body**
- `stockroom/reservations.py:{lookup}-{replay}`
- Worksheet: reach any client reusing a key · residue request · signal none → major
- Evidence: `reserve("A", 1, "K")` then `reserve("B", 5, "K")` returns the A
  reservation with 200. Nothing of B is held, and the response does not
  show the mismatch.
- Cross-ref: CMP (the key's contract in `docs/api.md`).

**LOG-002 · M · isolated — Releasing a reservation twice returns its stock twice**
- `stockroom/reservations.py:{rel_from}-{rel_put}` (no state check before `store.put`)
- Worksheet: reach a client retrying a release · residue request · signal none → major
- Evidence: `release(R)` twice raises available stock by twice the
  reservation's qty; both calls answer 200.

---

### Error handling (ERR) — 10/10 · 0 open

---

### Security (SEC) — 10/10 · 0 open

---

### Code pattern (PAT) — 10/10 · 0 open

---

### Concurrency safety (CON) — 6/10 · 1 open

**CON-001 · M · isolated — Two concurrent requests with one idempotency key both reserve**
- `stockroom/reservations.py:{lookup}`, `:{insert}` (the key is recorded after `_lock` is released)
- Worksheet: reach the order service retrying while the first request is in flight (each request has its own thread) · residue request (stock taken twice; the first reservation is no longer reachable by its key) · signal none → major
- Evidence: the first request with key K takes stock and releases `_lock`
  before recording K; a second request with K that acquires the lock in
  that gap misses `_by_key`, passes the stock check, and takes the stock
  again.

---

### Contract & compatibility (CMP) — 9/10 · 1 open

**CMP-001 · m · isolated — `docs/api.md` says release answers 204; it answers 200 with the reservation**
- `docs/api.md:{doc_204}`; `stockroom/server.py:{srv_200}`

## Credited as intentional (recorded to prevent re-litigation)

_None._

## Resolved findings (archive)

_None yet._

## History

| Date | Hash | LOG | ERR | SEC | PAT | CON | CMP | Worst | Avg |
|---|---|---|---|---|---|---|---|---|---|
| 2026-10-01 | {h} | 5 | 10 | 10 | 10 | 6 | 9 | LOG 5 | 8.3 |

Per-aspect baselines (diff basis for the next incremental review):
LOG, ERR, SEC, PAT, CON, CMP @ {h}, whole repo.
"""


def git(*args, date="2026-10-01T10:00:00+00:00"):
    env = dict(os.environ, GIT_AUTHOR_NAME="Dev", GIT_AUTHOR_EMAIL="dev@example.com",
               GIT_COMMITTER_NAME="Dev", GIT_COMMITTER_EMAIL="dev@example.com",
               GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    return subprocess.run(["git", *args], cwd=OUT, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def write(rel, text):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    git("init", "-q", "-b", "main")
    git("config", "commit.gpgsign", "false")
    write("README.md", README)
    write(".gitignore", "__pycache__/\n")
    write("stockroom/__init__.py", "")
    write("stockroom/reservations.py", RESERVATIONS)
    write("stockroom/store.py", STORE)
    write("stockroom/server.py", SERVER)
    write("tests/__init__.py", "")
    write("tests/test_reservations.py", TESTS)
    write("docs/api.md", API_DOC)
    git("add", "-A")
    git("commit", "-q", "-m", "stockroom: reservations with idempotency keys")
    h = git("rev-parse", "--short=7", "HEAD")
    write("docs/review/review.md", ledger(h))
    git("add", "-A")
    git("commit", "-q", "-m", f"stockroom review @{h}", date="2026-10-01T12:00:00+00:00")
    print(f"wrote {OUT} (code @{h}, ledger @{git('rev-parse', '--short=7', 'HEAD')})")


if __name__ == "__main__":
    main()
