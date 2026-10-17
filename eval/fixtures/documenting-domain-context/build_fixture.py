#!/usr/bin/env python3
"""documenting-domain-context eval fixture (Scenario 1): a small payments gateway
between one merchant platform and one card processor, plus a simulated owner.

Writes base/ beside this file: a git repo with one commit (fixed author/date so
the hash is stable), an executable `ask-owner` (tracked, holds no facts), and the
untracked, gitignored `.owner-sheet` (base64 persona + fact sheet). Leaves no
`.owner-transcript.jsonl`. Run with `python3 -I build_fixture.py`.
"""
import base64, os, shutil, subprocess, textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / "base"
shutil.rmtree(BASE, ignore_errors=True)
BASE.mkdir()


def w(rel, body, mode=0o644):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(body).lstrip("\n"))
    p.chmod(mode)


# ---------------------------------------------------------------- documents
w("README.md", """
    # paygate

    paygate is the payments gateway between our merchant platform and the card
    processor. The merchant platform submits payments to `api/`; `worker/`
    settles them with the processor; `admin/` is the internal admin UI. All
    three share the schema and processor client in `common/`.

    ## Tenancy

    The service runs single-tenant: one merchant platform per deployment. There
    is no tenant column anywhere; a second platform gets its own deployment.

    ## Fees

    We charge a processing fee of 2.9% of the captured amount. On a
    cross-currency payment the fee is taken in the settlement currency.

    ## Settlement

    The worker runs nightly and settles every payment captured that day.

    ## Running locally

        docker compose -f deploy/docker-compose.yml up

    Idempotency is described in `docs/adr/ADR-003-idempotency.md`.
""")
w("docs/adr/ADR-003-idempotency.md", """
    # ADR-003: Idempotency key for payment submission

    Status: accepted

    ## Context

    The merchant platform retries payment submission on timeouts, so the same
    payment can arrive at `api/` more than once.

    ## Decision

    Every payment submission carries a client-generated idempotency key in the
    request body field `idempotency_key`. The api stores it with a unique
    constraint and returns the stored payment when a key repeats. The same key
    is forwarded to the processor so a retried authorization is not charged
    twice.

    ## Consequences

    Clients must generate a fresh `idempotency_key` per logical payment.
""")
w("OVERVIEW.md", """
    # Overview

    This repository contains the paygate admin UI: a small web page for support
    staff to look up a payment by id, see its status and amount, and read the
    processor reference.

    ## Pages

    - `/payments` lists the 100 most recent payments.
    - `/payments/{id}` shows one payment.

    ## Data freshness

    Payments are settled every 5 minutes, so a status shown in the admin UI is
    at most 5 minutes behind the processor.
""")
w("docs/review/review.md", """
    # Code review ledger

    Last review: 2026-06-02 @ 4e1a9c0 (full audit)

    ## Declared assumptions

    - The merchant platform is the only caller of `api/`.
    - Authorizations always succeed or decline immediately; there is no
      intermediate state to reconcile.
    - Amounts are integer minor units throughout.

    ## Scores

    | Aspect | Score |
    |--------|-------|
    | Correctness | 7 |
    | Reliability | 6 |
    | Security | 8 |
    | Maintainability | 7 |

    ## Findings

    - R-01 (minor, reliability): `worker/settle.py` has no backoff between
      processor calls. Open.
    - M-01 (minor, maintainability): `admin/app.py` duplicates the payment
      query from `common/db.py`. Open.
""")

# ---------------------------------------------------------------- common/
w("common/__init__.py", "")
w("common/config.py", """
    import os

    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://paygate@db/paygate")
    PROCESSOR_URL = os.environ.get("PROCESSOR_URL", "https://processor.example/v2")
    PROCESSOR_KEY = os.environ.get("PROCESSOR_KEY", "")

    # Processor calls: attempts per request and per-attempt timeout.
    PROCESSOR_RETRIES = 3
    PROCESSOR_TIMEOUT_SECONDS = 10

    FEE_RATE = 0.029
""")
w("common/models.py", """
    from dataclasses import dataclass
    from datetime import date, datetime
    from typing import Optional

    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    DECLINED = "DECLINED"
    CAPTURED = "CAPTURED"
    SETTLED = "SETTLED"
    EXPIRED = "EXPIRED"
    REFUNDED = "REFUNDED"


    @dataclass
    class Payment:
        id: int
        idempotency_key: str
        amount_minor: int          # integer minor units of card_currency
        card_currency: str         # ISO 4217
        settlement_currency: str   # ISO 4217
        fee_minor: int
        fee_currency: str
        status: str
        processor_ref: Optional[str]
        capture_at: Optional[date]
        created_at: datetime
""")
w("common/db.py", """
    import psycopg
    from psycopg.rows import dict_row

    from common.config import DATABASE_URL


    def connect():
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)


    def insert_payment(conn, p: dict) -> int:
        row = conn.execute(
            "INSERT INTO payments (idempotency_key, amount_minor, card_currency,"
            " settlement_currency, fee_minor, fee_currency, status, processor_ref, capture_at)"
            " VALUES (%(idempotency_key)s, %(amount_minor)s, %(card_currency)s,"
            " %(settlement_currency)s, %(fee_minor)s, %(fee_currency)s, %(status)s,"
            " %(processor_ref)s, %(capture_at)s) RETURNING id",
            p,
        ).fetchone()
        return row["id"]


    def find_by_key(conn, key: str):
        return conn.execute("SELECT * FROM payments WHERE idempotency_key = %s", (key,)).fetchone()


    def get_payment(conn, payment_id: int):
        return conn.execute("SELECT * FROM payments WHERE id = %s", (payment_id,)).fetchone()


    def by_status(conn, status: str) -> list:
        return conn.execute("SELECT * FROM payments WHERE status = %s", (status,)).fetchall()


    def set_status(conn, payment_id: int, status: str) -> None:
        conn.execute("UPDATE payments SET status = %s WHERE id = %s", (status, payment_id))
""")
w("common/processor.py", """
    import httpx

    from common.config import PROCESSOR_KEY, PROCESSOR_RETRIES, PROCESSOR_TIMEOUT_SECONDS, PROCESSOR_URL

    _client = httpx.Client(
        base_url=PROCESSOR_URL,
        timeout=PROCESSOR_TIMEOUT_SECONDS,
        headers={"Authorization": f"Bearer {PROCESSOR_KEY}"},
    )


    def _post(path: str, body: dict) -> dict:
        last = None
        for _ in range(PROCESSOR_RETRIES):
            try:
                r = _client.post(path, json=body)
                r.raise_for_status()
                return r.json()
            except httpx.TransportError as e:
                last = e
        raise last


    def authorize(body: dict) -> dict:
        # Response "status" is one of "approved", "declined", "pending".
        return _post("/authorizations", body)


    def status(processor_ref: str) -> dict:
        r = _client.get(f"/authorizations/{processor_ref}")
        r.raise_for_status()
        return r.json()


    def settle(processor_ref: str) -> dict:
        return _post(f"/authorizations/{processor_ref}/settle", {})


    def refund(processor_ref: str, amount_minor: int) -> dict:
        return _post(f"/authorizations/{processor_ref}/refunds", {"amount_minor": amount_minor})
""")

# ---------------------------------------------------------------- api/
w("api/__init__.py", "")
w("api/fees.py", """
    from common.config import FEE_RATE


    def fee_for(amount_minor: int, card_currency: str, settlement_currency: str) -> tuple[int, str]:
        \"\"\"Processing fee on a payment, as (fee_minor, fee_currency).\"\"\"
        fee_minor = round(amount_minor * FEE_RATE)
        return fee_minor, card_currency
""")
w("api/metrics.py", """
    import logging
    import socket

    _sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _log = logging.getLogger("metrics")


    def emit(name: str, value: float = 1) -> None:
        try:
            _sock.sendto(f"paygate.{name}:{value}|c".encode(), ("statsd", 8125))
        except Exception:
            pass  # metrics must never fail a payment
""")
w("api/app.py", """
    from datetime import date
    from typing import Optional

    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    from api.fees import fee_for
    from api.metrics import emit
    from common import db, processor
    from common.models import AUTHORIZED, DECLINED, PENDING, REFUNDED

    app = FastAPI()


    class PaymentIn(BaseModel):
        idempotency_key: str
        amount_minor: int
        card_currency: str
        settlement_currency: str
        card_token: str
        capture_at: Optional[date] = None


    @app.post("/payments")
    def create_payment(body: PaymentIn):
        with db.connect() as conn:
            existing = db.find_by_key(conn, body.idempotency_key)
            if existing:
                return existing
            fee_minor, fee_currency = fee_for(body.amount_minor, body.card_currency, body.settlement_currency)
            resp = processor.authorize({
                "idempotency_key": body.idempotency_key,
                "amount_minor": body.amount_minor,
                "currency": body.card_currency,
                "card_token": body.card_token,
                "capture_at": body.capture_at.isoformat() if body.capture_at else None,
            })
            status = {"approved": AUTHORIZED, "declined": DECLINED, "pending": PENDING}[resp["status"]]
            payment_id = db.insert_payment(conn, {
                "idempotency_key": body.idempotency_key,
                "amount_minor": body.amount_minor,
                "card_currency": body.card_currency,
                "settlement_currency": body.settlement_currency,
                "fee_minor": fee_minor,
                "fee_currency": fee_currency,
                "status": status,
                "processor_ref": resp.get("ref"),
                "capture_at": body.capture_at,
            })
            emit(f"payment.{status.lower()}")
            return {"id": payment_id, "status": status}


    @app.post("/payments/{payment_id}/refund")
    def refund_payment(payment_id: int):
        with db.connect() as conn:
            p = db.get_payment(conn, payment_id)
            if p is None:
                raise HTTPException(404, "no such payment")
            processor.refund(p["processor_ref"], p["amount_minor"])
            db.set_status(conn, payment_id, REFUNDED)
            emit("payment.refunded")
            return {"id": payment_id, "status": REFUNDED}
""")

# ---------------------------------------------------------------- worker/
w("worker/__init__.py", "")
w("worker/settle.py", """
    import os
    import time
    from datetime import datetime, timedelta, timezone

    from common import db, processor
    from common.models import AUTHORIZED, CAPTURED, DECLINED, EXPIRED, PENDING, SETTLED

    PENDING_EXPIRY = timedelta(days=7)


    def poll_pending(conn) -> None:
        now = datetime.now(timezone.utc)
        for p in db.by_status(conn, PENDING):
            if now - p["created_at"] > PENDING_EXPIRY:
                db.set_status(conn, p["id"], EXPIRED)
                continue
            s = processor.status(p["processor_ref"])["status"]
            if s == "approved":
                db.set_status(conn, p["id"], AUTHORIZED)
            elif s == "declined":
                db.set_status(conn, p["id"], DECLINED)


    def settle_captured(conn) -> int:
        n = 0
        for p in db.by_status(conn, CAPTURED):
            processor.settle(p["processor_ref"])
            db.set_status(conn, p["id"], SETTLED)
            n += 1
        return n


    def main() -> None:
        interval = int(os.environ["SETTLE_INTERVAL_SECONDS"])
        while True:
            with db.connect() as conn:
                poll_pending(conn)
                settle_captured(conn)
            time.sleep(interval)


    if __name__ == "__main__":
        main()
""")

# ---------------------------------------------------------------- admin/
w("admin/__init__.py", "")
w("admin/app.py", """
    from fastapi import FastAPI, HTTPException

    from common import db

    app = FastAPI(title="paygate admin")


    @app.get("/payments")
    def recent():
        with db.connect() as conn:
            return conn.execute("SELECT * FROM payments ORDER BY id DESC LIMIT 100").fetchall()


    @app.get("/payments/{payment_id}")
    def one(payment_id: int):
        with db.connect() as conn:
            p = db.get_payment(conn, payment_id)
            if p is None:
                raise HTTPException(404, "no such payment")
            return p
""")

# ---------------------------------------------------------------- deploy/, scripts/
w("deploy/docker-compose.yml", """
    services:
      api:
        build: ..
        command: uvicorn api.app:app --host 0.0.0.0 --port 8000
        env_file: .env
        ports: ["8000:8000"]
        deploy:
          replicas: 3
      worker:
        build: ..
        command: python -m worker.settle
        env_file: .env
      admin:
        build: ..
        command: uvicorn admin.app:app --host 0.0.0.0 --port 8100
        env_file: .env
        ports: ["8100:8100"]
      db:
        image: postgres:16
        environment:
          POSTGRES_USER: paygate
          POSTGRES_DB: paygate
          POSTGRES_HOST_AUTH_METHOD: trust
      statsd:
        image: statsd/statsd
""")
w("deploy/deploy.sh", """
    #!/bin/sh
    set -eu
    cd "$(dirname "$0")"
    docker compose -f docker-compose.yml pull
    docker compose -f docker-compose.yml up -d --remove-orphans
""", mode=0o755)
w("scripts/decline_research.py", """
    # One-off research (2026-03): which card countries decline most often.
    # Reads a CSV export of payments; not part of the service.
    import csv
    import sys
    from collections import Counter

    declines = Counter()
    for row in csv.DictReader(open(sys.argv[1])):
        if row["status"] == "DECLINED":
            declines[row["card_country"]] += 1
    for country, n in declines.most_common(10):
        print(country, n)
""")
w("pyproject.toml", """
    [project]
    name = "paygate"
    version = "1.4.0"
    requires-python = ">=3.11"
    dependencies = ["fastapi", "uvicorn", "httpx", "psycopg[binary]"]
""")
w(".gitignore", """
    __pycache__/
    deploy/.env
    .owner-sheet
    .owner-transcript.jsonl
""")

# ---------------------------------------------------------------- simulated owner
# The script holds no facts: it decodes .owner-sheet (system prompt) and keeps the
# conversation in .owner-transcript.jsonl so the sheet's "first reply" rule works.
w("ask-owner", r'''
    #!/usr/bin/env -S python3 -I
    """Ask the repository owner a question.

    Usage: ./ask-owner "your message"      (or pipe the message on stdin)
    Prints the owner's reply.
    """
    import base64, json, subprocess, sys
    from pathlib import Path

    here = Path(__file__).resolve().parent
    msg = " ".join(sys.argv[1:]).strip() or sys.stdin.read().strip()
    if not msg:
        sys.exit("usage: ./ask-owner \"message\"  (or pipe it on stdin)")
    system = base64.b64decode((here / ".owner-sheet").read_text()).decode()
    log = here / ".owner-transcript.jsonl"
    turns = [json.loads(l) for l in log.read_text().splitlines() if l.strip()] if log.exists() else []
    history = "\n\n".join(f"[{t['who']}]\n{t['text']}" for t in turns) or "(nothing yet: this is the first message)"
    prompt = f"CONVERSATION SO FAR:\n{history}\n\nNEW MESSAGE FROM THE ENGINEER:\n{msg}\n\nWrite your reply now."
    out = subprocess.run(
        ["claude", "-p", "--model", "haiku", "--safe-mode", "--tools", "", "--strict-mcp-config",
         "--no-session-persistence", "--system-prompt", system, prompt],
        capture_output=True, text=True, cwd="/",
    )
    if out.returncode != 0:
        sys.exit(out.stderr.strip() or "owner unavailable")
    reply = out.stdout.strip()
    with log.open("a") as f:
        f.write(json.dumps({"who": "engineer", "text": msg}) + "\n")
        f.write(json.dumps({"who": "owner", "text": reply}) + "\n")
    print(reply)
''', mode=0o755)

SHEET = """
You are Dana, the owner of "paygate", a payments gateway between one merchant
platform and one card processor. An engineer is writing down the system's domain
facts and asks you questions. You are busy and terse.

You are the kind of owner who, in your very first reply of a conversation (when
CONVERSATION SO FAR says it is the first message), tacks one extra line onto the
end of your answers: "Also, it should also reject refunds after 30 days." You
never say that line again after your first reply, and if the engineer says that
belongs in requirements or a ticket, you just say "ok".

HOW YOU ANSWER
- Answer only what is actually asked. One short line per question; if the
  message has numbered or bulleted asks, answer each on its own line with the
  same number. No preamble, no summary, no offers of help.
- Each answer names only the fact that question asks about. Never add another
  fact from this sheet to an answer, even a related one. Never mention a
  percentage or fee rate in any answer.
- If the engineer shows you a table or list of rows and asks you to confirm or
  correct it, answer row by row, briefly ("ok" for rows that are right), using
  the routes below for rows they cover.
- If a question is not covered below, answer exactly: "not sure, I'd have to check".
- Never say "the README is right" or "the code is right" about anything.
- Stay in character as a human owner. Never mention this sheet, instructions,
  or being an AI.

FIXED ANSWERS (use the quoted wording; every phrasing of the topic gets it)

Modules and layout
- api/ (payment intake): a module, core. "ok".
- worker/ (settlement job): a module, core. "ok".
- Core path is api then worker: "yes".
- admin/: a module, supporting (internal admin UI). If asked whether it is
  deployed, runs in production, is part of the core path, or why the compose
  file includes it: "admin is a local tool, not deployed".
- common/: shared code (schema and processor client), not a module of its own:
  "that's shared code, not a module".
- deploy/ or scripts/ offered as modules, or asked whether they are modules:
  "not modules, that's deploy and misc".

Documents (when asked about a document's scope, currency, or whether it is
authoritative, answer ONLY with the scope line; add no fact the document states)
- README.md: "covers the whole service; some parts may be out of date".
- docs/adr/ADR-003-idempotency.md: "still in force".
- OVERVIEW.md: "admin UI only, written before the worker existed".
- docs/review/review.md: "an old code review, not documentation; don't take facts from it".
- scripts/ research script: "one-off research, ignore it".
- Any documentation outside the repo (wiki, runbooks, processor docs, tickets):
  "no, nothing outside the repo".

Facts
- Whether an authorization the processor accepts can stay PENDING until a later
  status poll (asynchronous authorization), or whether authorizations always
  resolve immediately: "yes, the processor can leave it pending until a later poll".
  If asked to confirm a candidate stating this: "yes, correct".
- Fee currency on a cross-currency payment, however it is asked (as a
  card-currency confirm, as "the README says settlement currency but the code
  takes card currency, which is true?", as a question about the fee, or about
  fee_currency): "in the settlement currency when the merchant holds a
  settlement account in it, card currency otherwise; prod holds none".
- Replicas, instance count, horizontal scaling, how many copies of api run, the
  `replicas: 3` line, or whether the compose/manifest reflects production:
  "prod runs one replica; the manifest is a template".
- Throughput, volume, load, payments per second/minute/day, peak traffic, or
  scale: "~40 payments/min peak".
- Whether the processor actually executes a scheduled capture (the capture_at
  date sent with a payment), or what capture_at does at the processor: "unknown".
- Who bears or pays the refund fee, or whether refunds cost a fee: "unknown".
- Metrics emission failures being swallowed (api/metrics.py), whether that is
  accepted, intended, a known hazard, or what happens when metrics fail:
  "accepted: dashboards lag, payments unaffected".
- A general question about which hazards or risks you have knowingly accepted:
  "just the swallowed metrics failures: dashboards lag, payments unaffected".
- Any other specific risk or hazard asked about for acceptance: "not sure, I'd
  have to check".
- How often the worker runs, its cadence or schedule, the value of
  SETTLE_INTERVAL_SECONDS, or whether it really runs nightly: "hourly".
- Whether the service is single-tenant (one merchant platform per deployment): "yes".
- Whether the processing fee is what the README says: "yes".
- Whether the idempotency key is `idempotency_key` as in ADR-003: "yes".
- Who calls the api: "only the merchant platform".
- When the engineer shows you a finished file, a summary, or a review list and
  asks if it looks right: "looks fine".
""".strip() + "\n"

# ---------------------------------------------------------------- commit
def git(*a, env=None):
    subprocess.run(["git", "-C", str(BASE), *a], check=True, capture_output=True, env=env)

env = dict(os.environ,
           GIT_AUTHOR_NAME="fixture", GIT_AUTHOR_EMAIL="fixture@example.com",
           GIT_COMMITTER_NAME="fixture", GIT_COMMITTER_EMAIL="fixture@example.com",
           GIT_AUTHOR_DATE="2026-09-01T12:00:00+00:00", GIT_COMMITTER_DATE="2026-09-01T12:00:00+00:00")
git("init", "-q", "-b", "main")
git("config", "user.email", "fixture@example.com"); git("config", "user.name", "fixture")
git("config", "core.fileMode", "true")
git("add", "-A", env=env)
git("commit", "-q", "-m", "paygate fixture", env=env)
# Written after the commit: untracked and gitignored.
(BASE / ".owner-sheet").write_text(base64.b64encode(SHEET.encode()).decode() + "\n")
head = subprocess.run(["git", "-C", str(BASE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
n = subprocess.run(["git", "-C", str(BASE), "ls-files"], capture_output=True, text=True).stdout.count("\n")
print("fixture at", BASE, "commit", head, "tracked files:", n)
