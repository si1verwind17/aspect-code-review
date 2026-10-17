#!/usr/bin/env python3
"""reviewing-code-by-aspect eval fixture: two-module FastAPI service with seeded defects, decoys and plants."""
import shutil, subprocess, sys, textwrap
from pathlib import Path
HERE = Path(__file__).resolve().parent; BASE = HERE / "base"
shutil.rmtree(BASE, ignore_errors=True); BASE.mkdir()
def w(rel, body):
    p = BASE / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(textwrap.dedent(body).lstrip("\n"))

w("README.md", """
    # shopsvc

    Order intake for a small storefront. `app/` is the HTTP API (FastAPI) the
    web client calls; `worker/` settles paid orders nightly; both share `common/`.
    Authentication is handled by the ingress sidecar, which sets `X-User-Id` on
    every request it forwards (see `deploy/`). Fees: a 3% processing fee on the
    order total.
""")
w("common/config.py", """
    import os
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://shop@db/shop")
    PAYMENT_URL = os.environ.get("PAYMENT_URL", "https://pay.example/v1")
    PAYMENT_KEY = os.environ["PAYMENT_KEY"]
    FEE_RATE = 0.03
    DISCOUNT_THRESHOLD = 100.0
    DISCOUNT_RATE = 0.10
    REGIONS = ["eu-west", "eu-central", "us-east", "us-west", "ap-south", "ap-east"]
""")
w("common/db.py", """
    import psycopg
    from common.config import DATABASE_URL

    def connect():
        return psycopg.connect(DATABASE_URL)
""")
w("common/models.py", """
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class Order:
        id: int
        user_id: str
        total: float
        status: str
        payment_ref: Optional[str] = None

    @dataclass
    class PaymentRequest:
        amount: float
        currency: str = "EUR"
        capture: bool = False   # authorize-only unless the caller asks to capture
""")
w("app/config.py", """
    from common.config import *  # noqa: F401,F403

    PAGE_SIZE = 50
""")
w("app/auth.py", """
    from fastapi import Header, HTTPException

    def current_user(x_user_id: str = Header(default="")) -> str:
        # Set by the ingress sidecar after it validates the session; see deploy/ingress.yaml.
        if not x_user_id:
            raise HTTPException(401, "missing identity")
        return x_user_id
""")
w("app/cache.py", """
    import hashlib

    _profiles: dict = {}   # process-wide profile cache

    def cacheKey(user_id: str, region: str) -> str:
        return hashlib.md5(f"{user_id}:{region}".encode()).hexdigest()  # cache key only, not security

    def getProfile(user_id: str, loader):
        if user_id not in _profiles:
            _profiles[user_id] = loader(user_id)
        return _profiles[user_id]

    def putProfile(user_id: str, profile) -> None:
        _profiles[user_id] = profile
""")
w("app/metrics.py", """
    import httpx

    def emit(name: str, value: float) -> None:
        try:
            httpx.post("http://metrics:9090/emit", json={"name": name, "value": value}, timeout=1)
        except Exception:
            pass  # fire-and-forget metrics, failure ok
""")
w("app/startup.py", """
    from common.config import REGIONS

    def validate_regions() -> None:
        # Startup sanity check over the (small, static) region list.
        for a in REGIONS:
            for b in REGIONS:
                if a != b and a.split("-")[0] == b.split("-")[0] and a == b.upper():
                    raise RuntimeError(f"conflicting regions {a} {b}")
""")
w("app/payments.py", """
    import httpx
    from common.config import PAYMENT_URL, PAYMENT_KEY
    from common.models import PaymentRequest

    def charge(req: PaymentRequest) -> dict:
        body = {"amount": req.amount, "currency": req.currency, "capture": req.capture}
        # Retry transient failures so a flaky gateway does not lose the sale.
        for attempt in range(3):
            try:
                r = httpx.post(f"{PAYMENT_URL}/charges", json=body, headers={"X-Key": PAYMENT_KEY}, timeout=5)
                r.raise_for_status()
                return r.json()
            except httpx.HTTPError:
                if attempt == 2:
                    raise
        raise RuntimeError("unreachable")
""")
w("app/repo.py", """
    from common import db

    def _col(name: str) -> str:
        return _qualify(name)

    def _qualify(name: str) -> str:
        return "o." + name

    def list_orders(table: str, user_id: str, sort_by: str) -> list:
        # table is a route parameter so operators can query archive tables too
        with db.connect() as conn:
            rows = conn.execute(f"SELECT id, user_id, total, status FROM {table} WHERE user_id = %s ORDER BY " + _col(sort_by), (user_id,)).fetchall()
        return rows

    def get_order(order_id: int):
        with db.connect() as conn:
            return conn.execute("SELECT id, user_id, total, status, payment_ref FROM orders WHERE id = %s", (order_id,)).fetchone()

    def search_orders(status: str) -> list:
        with db.connect() as conn:
            return conn.execute(f"SELECT id FROM orders WHERE status = '{status}'").fetchall()

    def get_profile(user_id: str) -> dict:
        with db.connect() as conn:
            row = conn.execute("SELECT region FROM profiles WHERE user_id = %s", (user_id,)).fetchone()
        return {"region": row[0] if row else "eu-west"}

    def insert_order(user_id: str, total: float, status: str) -> int:
        with db.connect() as conn:
            (oid,) = conn.execute("INSERT INTO orders (user_id, total, status) VALUES (%s,%s,%s) RETURNING id", (user_id, total, status)).fetchone()
            return oid

    def set_paid(order_id: int, payment_ref: str) -> None:
        with db.connect() as conn:
            conn.execute("UPDATE orders SET status='paid', payment_ref=%s, paid_at=now() WHERE id=%s", (payment_ref, order_id))
            conn.execute("INSERT INTO order_events (order_id, kind) VALUES (%s, 'paid')", (order_id,))
""")
w("app/orders.py", """
    from fastapi import APIRouter, Depends, HTTPException
    from app import repo, payments, metrics, cache
    from app.auth import current_user
    from app.config import DISCOUNT_THRESHOLD, DISCOUNT_RATE, FEE_RATE
    from common.models import PaymentRequest

    router = APIRouter()

    def price(total: float) -> float:
        # Orders at or above the threshold get the volume discount.
        if total < DISCOUNT_THRESHOLD:
            total = total * (1 - DISCOUNT_RATE)
        return round(total * (1 + FEE_RATE), 2)

    @router.post("/orders")
    def create(body: dict, user: str = Depends(current_user)):
        total = price(float(body["total"]))
        oid = repo.insert_order(user, total, "pending")
        # The gateway answers "authorized" here; the sale is complete from our side,
        # so we mark it paid and move on.
        resp = payments.charge(PaymentRequest(amount=total))
        try:
            repo.set_paid(oid, resp["id"])
        except Exception:
            pass
        metrics.emit("orders.created", 1)
        return {"id": oid, "status": "paid", "amount": total}

    @router.get("/orders/search")
    def search(status: str, user: str = Depends(current_user)):
        profile = cache.getProfile(user, lambda uid: repo.get_profile(uid))
        return {"region": profile["region"], "ids": [r[0] for r in repo.search_orders(status)]}

    @router.get("/orders/{order_id}")
    def get(order_id: int, user: str = Depends(current_user)):
        row = repo.get_order(order_id)
        if row is None:
            raise HTTPException(404)
        return {"id": row[0], "user_id": row[1], "total": row[2], "status": row[3]}

    @router.get("/orders")
    def list_(table: str = "orders", sort_by: str = "id", user: str = Depends(current_user)):
        return repo.list_orders(table, user, sort_by)

""")
w("app/main.py", """
    from fastapi import FastAPI
    from app.orders import router
    from app.startup import validate_regions

    app = FastAPI()
    validate_regions()
    app.include_router(router)
""")
w("app/tests/test_orders.py", """
    from app.orders import price

    def test_fee_applied():
        assert price(50.0) == round(50.0 * 0.9 * 1.03, 2)

    def test_threshold_boundary():
        assert price(100.0) == round(100.0 * 1.03, 2)
""")
w("worker/settle.py", """
    from common import db

    def settleBatch() -> int:
        with db.connect() as conn:
            rows = conn.execute("SELECT id FROM orders WHERE status='paid' AND settled_at IS NULL").fetchall()
            for (oid,) in rows:
                conn.execute("UPDATE orders SET settled_at=now() WHERE id=%s", (oid,))
                conn.execute("INSERT INTO order_events (order_id, kind) VALUES (%s,'settled')", (oid,))
        return len(rows)

    def runNightly() -> None:
        n = settleBatch()
        print(f"settled {n}")

    if __name__ == "__main__":
        runNightly()
""")
w("worker/tests/test_settle.py", """
    def test_settle_batch_marks_rows():
        assert True

    def test_nightly_runs():
        assert True

    def test_events_written():
        assert True
""")
w("deploy/initdb/01-schema.sql", """
    CREATE TABLE IF NOT EXISTS orders (
      id BIGSERIAL PRIMARY KEY,
      user_id TEXT NOT NULL,
      total NUMERIC(12,2) NOT NULL,
      status TEXT NOT NULL,
      payment_ref TEXT,
      settled_at TIMESTAMPTZ
    );
    CREATE TABLE IF NOT EXISTS profiles (
      user_id TEXT PRIMARY KEY,
      region TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS order_events (
      id BIGSERIAL PRIMARY KEY,
      order_id BIGINT REFERENCES orders(id),
      kind TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
""")
w("deploy/initdb/02-alter.sql", """
    -- added for the paid_at timestamp the API now writes
    ALTER TABLE orders ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;
""")
w("deploy/docker-compose.yml", """
    services:
      db:
        image: postgres:16-alpine
        environment: { POSTGRES_USER: shop, POSTGRES_DB: shop }
        volumes:
          - ./initdb:/docker-entrypoint-initdb.d
      app:
        build: ..
        command: uvicorn app.main:app --host 0.0.0.0 --port 8000
        env_file: .env
        depends_on: [db]
      worker:
        build: ..
        command: python -m worker.settle
        env_file: .env
        depends_on: [db]
""")
w("deploy/ingress.yaml", """
    # Ingress sidecar: validates the session cookie and forwards X-User-Id to app.
    apiVersion: v1
    kind: ConfigMap
    metadata: { name: ingress-auth }
    data:
      policy: |
        on_request: validate_session -> set_header X-User-Id
        upstream: app:8000
""")
w("pyproject.toml", """
    [project]
    name = "shopsvc"
    version = "0.2.0"
    dependencies = ["fastapi", "httpx", "psycopg[binary]"]
""")
w(".gitignore", "deploy/.env\n__pycache__/\n")
def git(*a): subprocess.run(["git","-C",str(BASE),*a],check=True,capture_output=True)
git("init","-q","-b","main"); git("config","user.email","fixture@example.com"); git("config","user.name","fixture")
git("add","-A"); git("commit","-q","-m","shopsvc fixture")
# dirty-tree setup edit (uncommitted)
(BASE/"app/config.py").write_text((BASE/"app/config.py").read_text() + "\ndef page_bounds(page: int) -> tuple[int, int]:\n    return (page * PAGE_SIZE, (page + 1) * PAGE_SIZE)\n")
print("fixture at", BASE, "files:", subprocess.run(["git","-C",str(BASE),"ls-files"],capture_output=True,text=True).stdout.count("\n"))
