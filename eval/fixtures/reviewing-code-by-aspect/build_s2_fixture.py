#!/usr/bin/env python3
"""Scenario 2 fixture (incremental re-review): stdlib-only Python orders service.

History: h1..h7 = the reviewed history (h1 = only full review, h2..h7 = six
incremental rounds; h7 = "commit 1", the per-aspect baseline), L = the prior
ledger commit, then the diff commits D1..D4 carrying (a)-(f) and F2.
"""
import os, shutil, subprocess, textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / "base-s2"
shutil.rmtree(BASE, ignore_errors=True)
BASE.mkdir()


def w(rel, body):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(body).lstrip("\n"))


def rm(rel):
    (BASE / rel).unlink()


def git(*a, date=None):
    env = dict(os.environ)
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    return subprocess.run(["git", "-C", str(BASE), *a], check=True, capture_output=True, text=True, env=env).stdout.strip()


def commit(msg, date):
    git("add", "-A")
    git("commit", "-q", "-m", msg, date=date)
    return git("rev-parse", "--short=7", "HEAD")


def ln(rel, needle, nth=1):
    hits = [i for i, l in enumerate((BASE / rel).read_text().splitlines(), 1) if needle in l]
    assert len(hits) >= nth, (rel, needle, hits)
    return hits[nth - 1]


# ---------------------------------------------------------------- static files
w(".gitignore", "__pycache__/\n*.db\n")
for pkg in ["app", "app/tests", "common", "worker", "worker/tests"]:
    w(f"{pkg}/__init__.py", "")

w("common/config.py", """
    import os

    DATABASE_PATH = os.environ.get("DATABASE_PATH", "shop.db")
    PAYMENT_URL = os.environ.get("PAYMENT_URL", "https://pay.example/v1")
    PAYMENT_KEY = os.environ.get("PAYMENT_KEY", "")
    METRICS_URL = os.environ.get("METRICS_URL", "http://127.0.0.1:9090/emit")
    BIND_HOST = "127.0.0.1"  # only the ingress sidecar in the same pod reaches the app
    BIND_PORT = 8000
    FEE_RATE = 0.03
    DISCOUNT_THRESHOLD = 100.0
    DISCOUNT_RATE = 0.10
    REGIONS = ["eu-west", "eu-central", "us-east", "us-west", "ap-south", "ap-east"]
""")
w("common/schema.sql", """
    CREATE TABLE IF NOT EXISTS orders (
      id INTEGER PRIMARY KEY,
      user_id TEXT NOT NULL,
      total REAL NOT NULL,
      status TEXT NOT NULL,
      payment_ref TEXT,
      settled_at TEXT
    );
    CREATE TABLE IF NOT EXISTS order_events (
      id INTEGER PRIMARY KEY,
      order_id INTEGER NOT NULL REFERENCES orders(id),
      kind TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS cart_items (
      user_id TEXT NOT NULL,
      sku TEXT NOT NULL,
      price REAL NOT NULL,
      qty INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS profiles (
      user_id TEXT PRIMARY KEY,
      region TEXT NOT NULL
    );
""")
w("common/db.py", """
    import sqlite3
    from contextlib import contextmanager
    from pathlib import Path

    from common import config

    SCHEMA = Path(__file__).with_name("schema.sql")


    @contextmanager
    def connect():
        conn = sqlite3.connect(config.DATABASE_PATH, timeout=5)
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()


    def init_schema() -> None:
        with connect() as conn:
            conn.executescript(SCHEMA.read_text())
""")
w("common/models.py", """
    from dataclasses import dataclass


    @dataclass
    class PaymentRequest:
        amount: float
        currency: str = "EUR"
""")
w("app/config.py", """
    from common.config import *  # noqa: F401,F403

    PAGE_SIZE = 50  # default page size for list endpoints
""")
w("app/errors.py", """
    class HttpError(Exception):
        def __init__(self, status: int, message: str):
            super().__init__(message)
            self.status = status
            self.message = message
""")
w("app/auth.py", """
    from app.errors import HttpError


    def current_user(headers) -> str:
        # X-User-Id is set by the ingress sidecar after it validates the session
        # (deploy/ingress.yaml); the app listens on localhost only.
        user = headers.get("X-User-Id", "")
        if not user:
            raise HttpError(401, "missing identity")
        return user
""")
w("app/cache.py", """
    import hashlib

    _profiles: dict = {}  # process-wide profile cache


    def cacheKey(user_id: str) -> str:
        return hashlib.md5(user_id.encode()).hexdigest()  # cache key only, not security


    def getProfile(user_id: str, loader) -> dict:
        key = cacheKey(user_id)
        if key not in _profiles:
            _profiles[key] = loader(user_id)
        return _profiles[key]
""")
w("app/metrics.py", """
    import json
    import urllib.request

    from common.config import METRICS_URL


    def emit(name: str, value: float) -> None:
        try:
            req = urllib.request.Request(METRICS_URL, data=json.dumps({"name": name, "value": value}).encode(), method="POST")
            urllib.request.urlopen(req, timeout=1).close()
        except Exception:
            pass  # fire-and-forget metrics, failure ok
""")
STARTUP = """
    from common.config import REGIONS


    def validate_regions() -> None:
    {comment}    for a in REGIONS:
            for b in REGIONS:
                if a != b and a.split("-")[0] == b.split("-")[0] and a == b.upper():
                    raise RuntimeError(f"conflicting regions {{a}} {{b}}")
"""
w("app/startup.py", STARTUP.format(comment=""))
PAYMENTS = """
    import json
    import urllib.error
    import urllib.request

    from common.config import PAYMENT_KEY, PAYMENT_URL
    from common.models import PaymentRequest


    def _post(path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{PAYMENT_URL}{path}",
            data=json.dumps(payload).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "X-Key": PAYMENT_KEY},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())


    def charge(req: PaymentRequest) -> dict:
        body = {"amount": req.amount, "currency": req.currency}
        # Retry transient failures so a flaky gateway does not lose the sale.
        for attempt in range(3):
            try:
                return _post("/charges", body)
            except (urllib.error.URLError, TimeoutError):
                if attempt == 2:
                    raise
        raise RuntimeError("unreachable")
"""
w("app/payments.py", PAYMENTS)

# repo.py pieces -----------------------------------------------------------
REPO_HEAD_PLAIN = """
    from common import db
"""
REPO_HEAD_RETRY = """
    import logging
    import sqlite3

    from common import db

    log = logging.getLogger(__name__)
"""
REPO_COMMON_A = """

    def cart_total(user_id: str) -> float:
        with db.connect() as conn:
            (total,) = conn.execute("SELECT COALESCE(SUM(price * qty), 0) FROM cart_items WHERE user_id = ?", (user_id,)).fetchone()
        return float(total)


    def insert_order(user_id: str, total: float, status: str) -> int:
        with db.connect() as conn:
            cur = conn.execute("INSERT INTO orders (user_id, total, status) VALUES (?, ?, ?)", (user_id, total, status))
            return cur.lastrowid
"""
SET_PAID_OK = """

    def set_paid(order_id: int, payment_ref: str) -> None:
        with db.connect() as conn:
            conn.execute("UPDATE orders SET status = 'paid', payment_ref = ? WHERE id = ?", (payment_ref, order_id))
            conn.execute("INSERT INTO order_events (order_id, kind) VALUES (?, 'paid')", (order_id,))
            conn.execute("DELETE FROM cart_items WHERE user_id = (SELECT user_id FROM orders WHERE id = ?)", (order_id,))
"""
# F2: parameters bound in the wrong order -> UPDATE matches no row, silently.
SET_PAID_F2 = """

    def set_paid(order_id: int, payment_ref: str) -> None:
        # Take the write lock up front (BEGIN IMMEDIATE) so the order update, its
        # event and the cart cleanup commit together or not at all.
        with db.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE orders SET payment_ref = ?, status = 'paid' WHERE id = ?", (order_id, payment_ref))
            conn.execute("INSERT INTO order_events (order_id, kind) VALUES (?, 'paid')", (order_id,))
            conn.execute("DELETE FROM cart_items WHERE user_id = (SELECT user_id FROM orders WHERE id = ?)", (order_id,))
"""
GET_ORDER_PLAIN = """

    def get_order(order_id: int):
        with db.connect() as conn:
            return conn.execute("SELECT id, user_id, total, status, payment_ref FROM orders WHERE id = ?", (order_id,)).fetchone()
"""
GET_ORDER_RETRY = """

    def get_order(order_id: int):
        for attempt in range({n}):
            try:
                with db.connect() as conn:
                    return conn.execute("SELECT id, user_id, total, status, payment_ref FROM orders WHERE id = ?", (order_id,)).fetchone()
            except sqlite3.OperationalError as e:
                log.warning("get_order(%s) attempt %d failed: %s", order_id, attempt + 1, e)
        return None
"""
SEARCH = """

    def search_orders(user_id: str, status: str) -> list:
        with db.connect() as conn:
            return conn.execute(f"SELECT id FROM orders WHERE user_id = ? AND status = '{{status}}'{order}", (user_id,)).fetchall()
"""
LIST_ORDERS = """

    def list_orders(user_id: str) -> list:
        with db.connect() as conn:
            return conn.execute("SELECT id, total, status FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
"""
PROFILE = """

    def get_profile(user_id: str) -> dict:
        with db.connect() as conn:
            row = conn.execute("SELECT region FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        return {"region": row[0] if row else "eu-west"}
"""


def repo(retry_n=None, f2=False, order="", listing=False):
    head = REPO_HEAD_RETRY if retry_n else REPO_HEAD_PLAIN
    get_order = GET_ORDER_RETRY.format(n=retry_n) if retry_n else GET_ORDER_PLAIN
    body = (head + REPO_COMMON_A + (SET_PAID_F2 if f2 else SET_PAID_OK) + get_order
            + SEARCH.format(order=order) + (LIST_ORDERS if listing else "") + PROFILE)
    w("app/repo.py", body)


# orders.py pieces ----------------------------------------------------------
ORDERS_HEAD = """
    from app import cache, metrics, payments, repo
    from app.config import DISCOUNT_RATE, DISCOUNT_THRESHOLD, FEE_RATE
    from app.errors import HttpError
    from common.models import PaymentRequest


    def price(total: float) -> float:
        # Orders at or above the threshold get the volume discount.
        if total < DISCOUNT_THRESHOLD:
            total = total * (1 - DISCOUNT_RATE)
        return round(total * (1 + FEE_RATE), 2)
"""
CREATE_SEED1 = """

    def create(params: dict, body: dict, user: str) -> dict:
        \"\"\"POST /orders: check out the caller's cart.\"\"\"
        subtotal = repo.cart_total(user)
        if subtotal <= 0:
            raise HttpError(400, "cart is empty")
        total = price(subtotal)
        oid = repo.insert_order(user, total, "pending")
        resp = payments.charge(PaymentRequest(amount=total))
        try:
            repo.set_paid(oid, resp["id"])
        except Exception:
            pass
        metrics.emit("orders.created", 1)
        return {"id": oid, "status": "paid", "amount": total}
"""
CREATE_FIXED = """

    def create(params: dict, body: dict, user: str) -> dict:
        \"\"\"POST /orders: check out the caller's cart.\"\"\"
        subtotal = repo.cart_total(user)
        if subtotal <= 0:
            raise HttpError(400, "cart is empty")
        total = price(subtotal)
        oid = repo.insert_order(user, total, "pending")
        resp = payments.charge(PaymentRequest(amount=total))
        try:
            repo.set_paid(oid, resp["id"])
        except Exception:
            # The order could not be recorded as paid: give the money back rather
            # than hold a charge no order row accounts for, then fail the request.
            payments.void(resp["id"])
            raise
        metrics.emit("orders.created", 1)
        return {"id": oid, "status": "paid", "amount": total}
"""
SEARCH_N1 = """

    def search(params: dict, body: dict, user: str) -> dict:
        \"\"\"GET /orders/search?status=...\"\"\"
        status = params.get("status", "pending")
        profile = cache.getProfile(user, repo.get_profile)
        ids = [row[0] for row in repo.search_orders(user, status)]
        orders = [{"id": i, "total": repo.get_order(i)[2]} for i in ids]
        return {"region": profile["region"], "orders": orders}
"""
SEARCH_IDS = """

    def search(params: dict, body: dict, user: str) -> dict:
        \"\"\"GET /orders/search?status=...\"\"\"
        status = params.get("status", "pending")
        profile = cache.getProfile(user, repo.get_profile)
        ids = [row[0] for row in repo.search_orders(user, status)]
        return {"region": profile["region"], "ids": ids}
"""
GET = """

    def get(params: dict, body: dict, user: str) -> dict:
        \"\"\"GET /orders/{order_id}\"\"\"
        row = repo.get_order(int(params["order_id"]))
        if row is None:
            raise HttpError(404, "order not found")
        return {"id": row[0], "user_id": row[1], "total": row[2], "status": row[3]}
"""
LIST_ = """

    def list_(params: dict, body: dict, user: str) -> dict:
        \"\"\"GET /orders: the caller's order history, newest first.\"\"\"
        rows = repo.list_orders(user)
        return {"orders": [{"id": r[0], "total": r[1], "status": r[2]} for r in rows]}
"""


def orders(fixed=False, n1=False, listing=False):
    w("app/orders.py", ORDERS_HEAD + (CREATE_FIXED if fixed else CREATE_SEED1)
      + (SEARCH_N1 if n1 else SEARCH_IDS) + GET + (LIST_ if listing else ""))


SERVER = """
    import json
    import logging
    import re
    {tb_import}from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlparse

    from app import orders
    from app.auth import current_user
    from app.config import BIND_HOST, BIND_PORT
    from app.errors import HttpError
    from app.startup import validate_regions
    from common import db

    log = logging.getLogger("shopsvc")

    ROUTES = [
        ("POST", re.compile(r"^/orders$"), orders.create),
    {list_route}    ("GET", re.compile(r"^/orders/search$"), orders.search),
        ("GET", re.compile(r"^/orders/(?P<order_id>\\d+)$"), orders.get),
    ]


    class Handler(BaseHTTPRequestHandler):
        def _dispatch(self, method: str) -> None:
            url = urlparse(self.path)
            for route_method, pattern, handler in ROUTES:
                match = pattern.match(url.path)
                if route_method == method and match:
                    break
            else:
                return self._send(404, {{"error": "not found"}})
            try:
                user = current_user(self.headers)
                params = {{k: v[0] for k, v in parse_qs(url.query).items()}}
                params.update(match.groupdict())
                raw = self.rfile.read(int(self.headers.get("Content-Length") or 0)) if method == "POST" else b""
                try:
                    body = json.loads(raw or b"{{}}")
                except json.JSONDecodeError:
                    raise HttpError(400, "body is not JSON")
                self._send(200, handler(params, body, user))
            except HttpError as e:
                self._send(e.status, {{"error": e.message}})
            except Exception:
    {unhandled}

        def do_GET(self) -> None:
            self._dispatch("GET")

        def do_POST(self) -> None:
            self._dispatch("POST")

        def _send(self, status: int, payload: dict) -> None:
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)


    def main() -> None:
        logging.basicConfig(level=logging.INFO)
        validate_regions()
        db.init_schema()
        ThreadingHTTPServer((BIND_HOST, BIND_PORT), Handler).serve_forever()


    if __name__ == "__main__":
        main()
"""
UNHANDLED_TB = """            self._send(500, {"error": traceback.format_exc()})"""
UNHANDLED_OK = """            log.exception("unhandled error on %s %s", method, url.path)
                self._send(500, {"error": "internal error"})"""


def server(traceback_leak=False, listing=False):
    w("app/server.py", SERVER.format(
        tb_import="import traceback\n    " if traceback_leak else "",
        list_route='    ("GET", re.compile(r"^/orders$"), orders.list_),\n    ' if listing else "",
        unhandled=UNHANDLED_TB if traceback_leak else UNHANDLED_OK,
    ).replace("\n    ", "\n    "))


w("worker/settle.py", """
    from common import db


    def settleBatch() -> int:
        with db.connect() as conn:
            rows = conn.execute("SELECT id FROM orders WHERE status = 'paid' AND settled_at IS NULL").fetchall()
            for (oid,) in rows:
                conn.execute("UPDATE orders SET settled_at = CURRENT_TIMESTAMP WHERE id = ?", (oid,))
                conn.execute("INSERT INTO order_events (order_id, kind) VALUES (?, 'settled')", (oid,))
        return len(rows)


    def runNightly() -> None:
        print(f"settled {settleBatch()}")


    if __name__ == "__main__":
        runNightly()
""")
w("worker/import_legacy.py", """
    \"\"\"One-off import of orders exported from the pre-2026 storefront (run by hand).\"\"\"
    import csv
    import sys

    from common import db


    def legacy_total(subtotal: float) -> float:
        # Legacy orders were contracted fee-free (finance sign-off FIN-12): no processing fee here.
        return round(subtotal, 2)


    def import_file(path: str) -> int:
        count = 0
        with open(path, newline="") as f, db.connect() as conn:
            for row in csv.DictReader(f):
                conn.execute(
                    "INSERT INTO orders (user_id, total, status, payment_ref) VALUES (?, ?, 'paid', ?)",
                    (row["user_id"], legacy_total(float(row["subtotal"])), row["legacy_ref"]),
                )
                count += 1
        return count


    if __name__ == "__main__":
        print(f"imported {import_file(sys.argv[1])}")
""")
w("app/tests/test_orders.py", """
    import os
    import tempfile
    import unittest

    from app import orders, repo
    from app.auth import current_user
    from app.errors import HttpError
    from common import config, db


    class DbTestCase(unittest.TestCase):
        def setUp(self):
            fd, self.path = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            self._saved = config.DATABASE_PATH
            config.DATABASE_PATH = self.path
            db.init_schema()

        def tearDown(self):
            config.DATABASE_PATH = self._saved
            os.remove(self.path)


    class OrdersTest(DbTestCase):
        def test_get_missing_order_is_404(self):
            with self.assertRaises(HttpError) as ctx:
                orders.get({"order_id": "999"}, {}, "u1")
            self.assertEqual(ctx.exception.status, 404)

        def test_search_lists_only_callers_orders(self):
            mine = repo.insert_order("u1", 10.0, "pending")
            repo.insert_order("u2", 20.0, "pending")
            self.assertEqual(orders.search({"status": "pending"}, {}, "u1")["ids"], [mine])

        def test_cart_total_sums_items(self):
            with db.connect() as conn:
                conn.execute("INSERT INTO cart_items VALUES ('u1', 'a', 2.5, 4), ('u1', 'b', 1.0, 1), ('u2', 'c', 9.0, 1)")
            self.assertEqual(repo.cart_total("u1"), 11.0)

        def test_empty_cart_is_rejected(self):
            with self.assertRaises(HttpError) as ctx:
                orders.create({}, {}, "u1")
            self.assertEqual(ctx.exception.status, 400)


    class AuthTest(unittest.TestCase):
        def test_missing_identity_is_401(self):
            with self.assertRaises(HttpError) as ctx:
                current_user({})
            self.assertEqual(ctx.exception.status, 401)

        def test_forwarded_identity_is_used(self):
            self.assertEqual(current_user({"X-User-Id": "u1"}), "u1")
""")
w("worker/tests/test_settle.py", """
    import unittest


    class SettleTest(unittest.TestCase):
        def test_settle_batch_marks_rows(self):
            assert True

        def test_nightly_runs(self):
            assert True

        def test_events_written(self):
            assert True
""")
README = """
    # shopsvc

    Order checkout for a small storefront. `app/` is the HTTP API the web
    client calls; `worker/` settles paid orders nightly; both share `common/`.
    Standard library only (Python 3.12+). Run the tests from the repo root with
    `python3 -m unittest`.

    Pricing: orders at or above 100.00 get a 10% volume discount; a 3%
    processing fee is then added to the total and borne by the customer.
{auth}"""
README_AUTH = """
    Authentication is handled by the ingress sidecar (`deploy/`): it validates
    the session cookie and forwards `X-User-Id` to the app, which listens on
    localhost inside the same pod and never sees unauthenticated traffic.
"""
w("README.md", README.format(auth=""))
APP_YAML = """
    apiVersion: apps/v1
    kind: Deployment
    metadata: {{ name: shopsvc }}
    spec:
      replicas: {replicas}
      selector: {{ matchLabels: {{ app: shopsvc }} }}
      template:
        metadata: {{ labels: {{ app: shopsvc }} }}
        spec:
          containers:
            - name: app
              image: shopsvc:latest
              command: ["python3", "-m", "app.server"]
              env:
                - {{ name: DATABASE_PATH, value: /data/shop.db }}
              volumeMounts: [{{ name: data, mountPath: /data }}]
            - name: ingress-auth
              image: ingress-auth:1.4
              args: ["--config", "/etc/ingress/policy"]
              ports: [{{ containerPort: 8443 }}]
              volumeMounts: [{{ name: ingress-policy, mountPath: /etc/ingress }}]
          volumes:
            - name: data
              persistentVolumeClaim: {{ claimName: shop-data }}
            - name: ingress-policy
              configMap: {{ name: ingress-auth }}
"""
w("deploy/app.yaml", APP_YAML.format(replicas=1))
w("deploy/ingress.yaml", """
    # Ingress sidecar: validates the session cookie and forwards X-User-Id to the app.
    apiVersion: v1
    kind: ConfigMap
    metadata: { name: ingress-auth }
    data:
      policy: |
        on_request: validate_session -> set_header X-User-Id
        upstream: 127.0.0.1:8000
""")
w("deploy/worker.yaml", """
    apiVersion: batch/v1
    kind: CronJob
    metadata: { name: shopsvc-settle }
    spec:
      schedule: "0 2 * * *"
      jobTemplate:
        spec:
          template:
            spec:
              restartPolicy: OnFailure
              containers:
                - name: settle
                  image: shopsvc:latest
                  command: ["python3", "-m", "worker.settle"]
                  env:
                    - { name: DATABASE_PATH, value: /data/shop.db }
                  volumeMounts: [{ name: data, mountPath: /data }]
              volumes:
                - name: data
                  persistentVolumeClaim: { claimName: shop-data }
""")
w("Dockerfile", """
    FROM python:3.12-slim
    WORKDIR /srv
    COPY . .
    CMD ["python3", "-m", "app.server"]
""")

git("init", "-q", "-b", "main")
git("config", "user.email", "fixture@example.com")
git("config", "user.name", "fixture")
git("config", "commit.gpgsign", "false")

# ---------------------------------------------------------------- reviewed history
repo(retry_n=5)
orders(n1=True)
server(traceback_leak=True)
H = {}
H[1] = commit("shopsvc: initial import", "2026-09-19T10:00:00")
repo()
H[2] = commit("Let order lookup errors propagate instead of retrying into a 404", "2026-09-22T10:00:00")
server()
H[3] = commit("Log unhandled errors server-side; return a generic 500 body", "2026-09-25T10:00:00")
w("README.md", README.format(auth=README_AUTH))
H[4] = commit("README: document the ingress sidecar auth model", "2026-09-28T10:00:00")
orders()
H[5] = commit("search: return ids only (drop per-id total lookup)", "2026-10-01T10:00:00")
w("deploy/app.yaml", APP_YAML.format(replicas=3))
H[6] = commit("deploy: run three app replicas", "2026-10-05T10:00:00")
w("app/startup.py", STARTUP.format(comment="    # Startup sanity check over the (small, static) region list.\n    "))
H[7] = commit("startup: note why the region check is quadratic", "2026-10-08T10:00:00")
C1 = H[7]

# line refs at C1 for the ledger
L = dict(
    price=ln("app/orders.py", "if total < DISCOUNT_THRESHOLD"),
    price_comment=ln("app/orders.py", "at or above the threshold"),
    swallow=ln("app/orders.py", "except Exception:"),
    set_paid_call=ln("app/orders.py", "repo.set_paid(oid"),
    paid_resp=ln("app/orders.py", '"status": "paid"'),
    retry=ln("app/payments.py", "for attempt in range(3)"),
    charge_def=ln("app/payments.py", "def charge("),
    amount=ln("app/payments.py", '"amount": req.amount'),
    sqli=ln("app/repo.py", "AND status = '{status}'"),
    search_status=ln("app/orders.py", 'params.get("status"'),
    get_order_call=ln("app/orders.py", "repo.get_order(int("),
    get_ret=ln("app/orders.py", 'return {"id": row[0], "user_id"'),
    cache_dict=ln("app/cache.py", "_profiles: dict"),
    cache_put=ln("app/cache.py", "_profiles[key] = loader"),
    md5=ln("app/cache.py", "hashlib.md5"),
    cachekey=ln("app/cache.py", "def cacheKey"),
    getprofile=ln("app/cache.py", "def getProfile"),
    settlebatch=ln("worker/settle.py", "def settleBatch"),
    runnightly=ln("worker/settle.py", "def runNightly"),
    metrics=ln("app/metrics.py", "fire-and-forget"),
    legacy=ln("worker/import_legacy.py", "def legacy_total"),
    legacy_c=ln("worker/import_legacy.py", "FIN-12"),
    auth=ln("app/auth.py", 'headers.get("X-User-Id"'),
    replicas=ln("deploy/app.yaml", "replicas:"),
    tsq1=ln("worker/tests/test_settle.py", "def test_settle_batch_marks_rows"),
    startup=ln("app/startup.py", "for a in REGIONS"),
)

# ---------------------------------------------------------------- prior ledger
h = H
LEDGER = f"""# Code Review Ledger

Method: aspect-scored review — severity sets the band, count refines within
it; scores derive from open findings by fixed arithmetic. This document is
the persistent ledger: scope, assumptions, overrides, open findings, archive,
history. Finding IDs are stable and never reused. Keep the section names and
order of this template — incremental reviews and future maintainers navigate
by them.

## Summary — 2026-10-09 @ {h[7]} (incremental, 10 aspects, scope: whole repo)

**Worst aspect(s): Error handling (ERR) and Security (SEC) at 2/10.**
ERR-001 — a failed `set_paid` after a successful charge is swallowed and the
response still says paid. ERR-002 — the non-idempotent gateway charge is
retried on timeout. SEC-001 — the `status` query param is spliced into SQL.
SEC-002 — any caller reads any order by id. LOG-001 — the volume discount is
applied below the threshold. MEM-001 — the profile cache never evicts.

Round 7 (incremental @ {h[7]}, 2026-10-09). The diff since {h[6]} only adds a
comment to `app/startup.py`; nothing to re-check beyond that file and no
finding changed. Added a TSQ candidate for the gateway charge request (no
test pins the amount sent to the payment API). Its mutation is named but was
not run this round — the suite run was deferred — so it stays a candidate and
is not scored. All ten scores unchanged from round 6; ERR-001 and ERR-002 are
still open and still the worst findings in the repo.

Round 6 (incremental @ {h[6]}, 2026-10-06). The only change was
`deploy/app.yaml`. No application code changed, so no aspect had a diff to
review and the deployment declaration was carried forward as it stood. No
finding opened or resolved; scores unchanged. ERR-001 still open.

Round 5 (incremental @ {h[5]}, 2026-10-02). CPU-001 resolved: `search` no
longer calls `get_order` once per matching id; it returns the ids only. CPU
returns to 10 and the average rises from 6.1 to 6.5. Re-checked SEC-001 in
the same diff (search path) — still open, the splice is untouched. ERR-001
and ERR-002 carried forward unchanged.

Round 4 (incremental @ {h[4]}, 2026-09-29). README now documents the ingress
sidecar. The auth model declaration was amended in this round (see Declared
assumptions): the round-1 declaration was wrong. Under the corrected
perimeter model the missing in-code authn is not a finding; object-level
authorization stays in scope, so SEC-002 stands unchanged. Scores unchanged.

Round 3 (incremental @ {h[3]}, 2026-09-26). SEC-003 resolved: the server now
logs unhandled exceptions and returns a generic 500 body instead of the
Python traceback. SEC stays at 2 — SEC-001 and SEC-002 are both critical and
still open. No other diff.

Round 2 (incremental @ {h[2]}, 2026-09-23). ERR-003 resolved: `get_order` no
longer retries five times and reports a database failure as 404; errors now
propagate to the server's 500 handler. ERR stays at 2 because ERR-001 and
ERR-002 are still critical. A test for the 404 path already existed.

Round 1 (full review @ {h[1]}, 2026-09-20). First full pass over the whole
repo with ten aspects (LOG, ERR, SEC, PAT, CON, CMP, MEM, CPU, TSQ, FMT).
Found six criticals (LOG-001, ERR-001, ERR-002, SEC-001, SEC-002, MEM-001),
four majors (ERR-003, SEC-003, CPU-001, TSQ-001) and one minor (FMT-001).
Credited three intentional decisions (metrics swallow, MD5 cache key,
fee-free legacy import). Startup region validation suppressed as a cold path.
The checkout journey carries most of the risk: the discount is inverted
(LOG-001), the charge is retried without an idempotency key (ERR-002), and a
failed `set_paid` is swallowed so the customer is told "paid" while the row
stays pending (ERR-001). The search path splices `status` into SQL (SEC-001)
and the single-order read has no ownership check (SEC-002). The profile
cache grows with the user population (MEM-001). Worker tests are
tautological (TSQ-001). Naming drift in two modules is one minor (FMT-001).
The owner confirmed snake_case and the startup suppression the next day
(User overrides). Fix order recommended to the owner: ERR-001, ERR-002,
SEC-001, SEC-002, then LOG-001 and MEM-001.

| Aspect | Score | Worst open | Open findings |
|---|---|---|---|
| Logic correctness (LOG) | **3** | critical | LOG-001 C |
| Error handling (ERR) | **2** | critical | ERR-001 C, ERR-002 C |
| Security (SEC) | **2** | critical | SEC-001 C, SEC-002 C |
| Code pattern (PAT) | **10** | — | — |
| Concurrency safety (CON) | **10** | — | — |
| Contract & compatibility (CMP) | **10** | — | — |
| Memory (MEM) | **3** | critical | MEM-001 C |
| CPU (CPU) | **10** | — | — |
| Test quality (TSQ) | **6** | major | TSQ-001 M |
| Format consistency (FMT) | **9** | minor | FMT-001 m (w) |

Average (trend only, never the headline): **6.5**.

## Review scope

Whole repo.

Context: declared from code (no owner-confirmed context).

## Declared assumptions (scout pass @ {h[1]}, 2026-09-20)

Evidence-based detections; each states the weakest claim its evidence
supports. Override any of these in User overrides — overrides persist and
bind future reviews.

- **Language(s)**: Python 3, standard library only; packages `app/` (HTTP
  API on `http.server`), `worker/` (nightly settle, one-off legacy import),
  `common/` (config, SQLite access, models, schema); ~20 files.
- **House pattern standard**: Python — PEP 8 snake_case functions,
  module-level functions for data access (`app/repo.py`), handlers as plain
  functions routed from `app/server.py`; evidence: dominant pattern across
  `app/`, `common/`, `worker/`; no linter config in the repo.
- **Auth model**: perimeter — the ingress sidecar validates the session and
  forwards `X-User-Id`; `app/auth.py:{L['auth']}` only requires the header.
  Evidence: `deploy/ingress.yaml`, the `ingress-auth` container in
  `deploy/app.yaml`, README. (Amended @{h[4]}: the earlier declaration —
  "in-code session-token auth in `app/auth.py`" — was wrong; `app/auth.py`
  never validated a token, and the README now documents the sidecar.)
- **Deployment model**: assumed a single app replica behind the ingress
  sidecar, sharing one SQLite file on a volume with the nightly worker;
  basis: `deploy/app.yaml:{L['replicas']}` `replicas: 1` and
  `deploy/worker.yaml` (capability evidence only — the manifests show the
  code supports Kubernetes, not that it runs there). Scale assumed: one
  storefront; order history and the user population grow with time.
- **Consumed contract surfaces**: HTTP API for the web client
  (`POST /orders`, `GET /orders/search`, `GET /orders/{{id}}`); outbound:
  payment gateway `POST /charges`, metrics endpoint.
- **Tests**: `unittest` suites in `app/tests/` and `worker/tests/`, run from
  the repo root with `python3 -m unittest`; app tests use a temp SQLite
  file; worker tests assert nothing (TSQ-001).
- **Exclusions**: none — no generated or vendored code.
- **Domain facts**: 10% volume discount at or above 100.00, then a 3%
  processing fee borne by the customer (README, `app/orders.py:{L['price_comment']}`);
  the gateway takes `POST /charges` with no idempotency key in the request
  (`app/payments.py`); legacy imported orders are fee-free (FIN-12).
- **Sweeps run**:
  - Raw identifier splices · `f".*(FROM|INTO|UPDATE|TABLE|JOIN)` and
    `" \\+ .*(FROM|WHERE)` · `*.py` · 1 hit (`app/repo.py:{L['sqli']}`, a value
    splice, filed as SEC-001) · 0 identifier splices.
  - Failure collapsed to a benign value · `except .*:\\s*(pass|return (None|\\[\\]|\\{{\\}}|False))`
    · `*.py` · 2 hits (`app/orders.py:{L['swallow']}` → ERR-001;
    `app/metrics.py:{L['metrics']}` → credited).
  - Ungated tests touching real systems · `import (sqlite3|urllib|http)` in
    `*/tests/*` · 0 hits (app tests use a temp file via `common.db`).
  - Retry budget vs caller deadline · `range\\(|timeout=` · `*.py` · charge
    3 × 5 s = 15 s worst case; no caller deadline declared in the repo · no lead.
  - Caller-supplied clock or identity · request params reaching persistence
    · `order_id` path param → SEC-002; `status` → SEC-001.
- **External-state journeys**: checkout (`POST /orders`: cart total →
  insert pending order → gateway charge → `set_paid` → metrics); nightly
  settle (paid → settled); legacy import (CSV → paid orders). No empty cells.
- **Scoring interpretation**: none → 10; minors only → 9 flat (listed and
  counted, never deducted); within the worst open C/M tier each *verified*
  finding counts one unit (widespread majors count two; doubling never
  applies to criticals); score = band start − step × (units − 1), clamped
  at the band floor (critical 3/−1/0, major 6/−1/4). The first unit is free
  — it sets the band: a single widespread major is 2 units → 6 − 1×1 = 5,
  never 4. Unverified C/M claims are listed as candidates and do not
  count.

## User overrides

- FMT · the function-naming standard is PEP 8 snake_case in every Python
  package, `worker/` included — owner, 2026-09-21.
- CPU · `app/startup.py` region validation runs once at boot over a fixed
  six-entry list; do not review it for complexity — owner, 2026-09-21.

## Open findings

Severity: C = critical, M = major, m = minor; (w) = widespread (counts
double). All findings open @ {h[7]}; finding bodies stay pinned to their
discovery hash. Aspect sections stay in catalog order (same as the summary
table); a `---` rule before each aspect header keeps the section boundary
visible mid-scroll.

---

### Logic correctness (LOG) — 3/10 · 1 open

**LOG-001 · C · isolated — volume discount applied below the threshold instead of at or above it**
- `app/orders.py:{L['price']}` `if total < DISCOUNT_THRESHOLD:` (found @{h[1]})
- Worksheet: reach `POST /orders`, every checkout · residue external (the
  gateway charges the wrong amount) · signal none → critical
- Intent: comment at `app/orders.py:{L['price_comment']}` and README ("at or above
  100.00"). Failing input: cart 150.00 → charged 154.50 (no discount)
  instead of 139.05; cart 50.00 → charged 46.35, a discount it should not get.

---

### Error handling (ERR) — 2/10 · 2 open

**ERR-001 · C · isolated — `set_paid` failure swallowed after the charge succeeds**
- `app/orders.py:{L['swallow']}` `except Exception: pass` around
  `repo.set_paid(oid, resp["id"])` (`app/orders.py:{L['set_paid_call']}`) (found @{h[1]})
- Worksheet: reach `POST /orders` when the SQLite write fails after the
  gateway charged · residue external (money taken; order row stays
  `pending` with no `payment_ref`, never settled) · signal none (response
  `"status": "paid"` at `app/orders.py:{L['paid_resp']}`) → critical
- Failing input: `set_paid` raises `sqlite3.OperationalError: database is
  locked` → 200 `{{"status": "paid"}}`; the orders row stays `pending`.
- Cross-ref: TSQ (the failure path has no test).

**ERR-002 · C · isolated — non-idempotent gateway charge retried on timeout**
- `app/payments.py:{L['retry']}` `for attempt in range(3)` around `POST /charges`,
  no idempotency key (found @{h[1]})
- Worksheet: reach `POST /orders` when the gateway accepts the charge but
  the response read times out · residue external (customer charged up to
  three times) · signal none → critical
- Failing input: gateway commits the charge, response exceeds the 5 s
  timeout → `TimeoutError` → second `POST /charges` with the same body.

---

### Security (SEC) — 2/10 · 2 open

**SEC-001 · C · isolated — SQL injection through the `status` query param**
- `app/repo.py:{L['sqli']}` f-string splice of `status` (found @{h[1]})
- Worksheet: reach any authenticated caller of `GET /orders/search` ·
  residue external (other customers' orders disclosed across the trust
  boundary) · signal none → critical
- Path: request param `status` (`app/orders.py:{L['search_status']}`) → SQL string at
  `app/repo.py:{L['sqli']}`. Input `status=' OR 1=1 --` returns every user's order ids.

**SEC-002 · C · isolated — `GET /orders/{{id}}` returns any customer's order (IDOR)**
- `app/orders.py:{L['get_order_call']}` fetch by id with no ownership check; response
  includes `user_id`, `total`, `status` (`app/orders.py:{L['get_ret']}`) (found @{h[1]})
- Worksheet: reach any authenticated caller; ids are sequential integers ·
  residue external (another customer's order disclosed) · signal none →
  critical
- Path: path param `order_id` → `repo.get_order` → response. The sidecar
  authenticates the caller; it cannot know which orders the caller owns.

---

### Code pattern (PAT) — 10/10 · 0 open

_No open findings._

---

### Concurrency safety (CON) — 10/10 · 0 open

_No open findings._

---

### Contract & compatibility (CMP) — 10/10 · 0 open

_No open findings._

---

### Memory (MEM) — 3/10 · 1 open

**MEM-001 · C · isolated — process-wide profile cache keyed by user, never evicted**
- `app/cache.py:{L['cache_dict']}` `_profiles` dict; insert at `app/cache.py:{L['cache_put']}` (found @{h[1]})
- Worksheet: reach every `GET /orders/search` by a distinct user · residue
  process (memory grows with the user population until the process is
  killed) · signal none → critical
- Scale: one entry per distinct `X-User-Id`; the user population grows with
  time and nothing removes an entry.

---

### CPU (CPU) — 10/10 · 0 open

CPU-001 resolved — see archive.

---

### Test quality (TSQ) — 6/10 · 1 open

**TSQ-001 · M · isolated — settle tests assert nothing**
- `worker/tests/test_settle.py:{L['tsq1']}` — all three tests are `assert True` (found @{h[1]})
- Worksheet: reach load-bearing (`settleBatch` is the only paid → settled
  transition) · residue request · signal none → major
- Mutation: delete the `UPDATE orders SET settled_at` line in
  `worker/settle.py` → suite stays green (run @{h[1]}).

**Candidates (unverified, not scored)**
- TSQ · M · gateway charge request untested — no test pins the amount sent
  to the payment API · `app/payments.py:{L['amount']}` — named mutation: in
  `charge()`, send `"amount": round(req.amount)` instead of
  `"amount": req.amount`; not run this round (suite run deferred). Run it in
  a scratch copy: green confirms the major, red refutes it.

---

### Format consistency (FMT) — 9/10 · 1 open

**FMT-001 · m · widespread — camelCase function names in two modules (house standard snake_case)**
- `app/cache.py:{L['cachekey']}` `cacheKey`, `app/cache.py:{L['getprofile']}` `getProfile`
- `worker/settle.py:{L['settlebatch']}` `settleBatch`, `worker/settle.py:{L['runnightly']}` `runNightly`
- Widespread: spans `app/` and `worker/` (label descriptive on a minor).

## Credited as intentional (recorded to prevent re-litigation)

- `app/metrics.py:{L['metrics']}` `emit()` swallows every failure — the comment
  `# fire-and-forget metrics, failure ok` names the accepted hazard (lost
  metric points); settles the would-be ERR swallow finding.
- `app/cache.py:{L['md5']}` MD5 in `cacheKey()` — a cache key, not a security
  control; settles the would-be SEC weak-hash finding.
- `worker/import_legacy.py:{L['legacy']}` `legacy_total()` adds no processing fee —
  the comment at line {L['legacy_c']} records the decision (legacy orders were
  contracted fee-free, finance sign-off FIN-12); settles the would-be LOG
  finding "fee missing on imported orders".

## Resolved findings (archive)

One line per resolved finding — `<ID> · <C|M|m> · <title> · <files> ·
resolved @<hash>`; full bodies live in this document's git history. A
reintroduced defect reopens its ID here (moves back to Open findings with
`reopened @<hash>`), never gets a new one.

- ERR-003 · M · `get_order` retries a failed read five times with no backoff, logging each attempt, then reports the database failure as 404 not found · app/repo.py, app/orders.py · resolved @{h[2]}
- SEC-003 · M · unhandled exceptions return the Python traceback to the client · app/server.py · resolved @{h[3]}
- CPU-001 · M · `search` issues one `get_order` query per matching id (N+1) on the request path · app/orders.py · resolved @{h[5]}

## History

| Date | Hash | LOG | ERR | SEC | PAT | CON | CMP | MEM | CPU | TSQ | FMT | Worst | Avg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-20 | {h[1]} (full) | 3 | 2 | 2 | 10 | 10 | 10 | 3 | 6 | 6 | 9 | ERR, SEC 2 | 6.1 |
| 2026-09-23 | {h[2]} | 3 | 2 | 2 | 10 | 10 | 10 | 3 | 6 | 6 | 9 | ERR, SEC 2 | 6.1 |
| 2026-09-26 | {h[3]} | 3 | 2 | 2 | 10 | 10 | 10 | 3 | 6 | 6 | 9 | ERR, SEC 2 | 6.1 |
| 2026-09-29 | {h[4]} | 3 | 2 | 2 | 10 | 10 | 10 | 3 | 6 | 6 | 9 | ERR, SEC 2 | 6.1 |
| 2026-10-02 | {h[5]} | 3 | 2 | 2 | 10 | 10 | 10 | 3 | 10 | 6 | 9 | ERR, SEC 2 | 6.5 |
| 2026-10-06 | {h[6]} | 3 | 2 | 2 | 10 | 10 | 10 | 3 | 10 | 6 | 9 | ERR, SEC 2 | 6.5 |
| 2026-10-09 | {h[7]} | 3 | 2 | 2 | 10 | 10 | 10 | 3 | 10 | 6 | 9 | ERR, SEC 2 | 6.5 |

Per-aspect baselines (diff basis for the next incremental review):
LOG, ERR, SEC, PAT, CON, CMP, MEM, CPU, TSQ, FMT @ {h[7]} — whole repo.
"""
w("docs/review/review.md", LEDGER)
w("docs/review/.gitignore", "*.html\n*.json\n")
LEDGER_C = commit("Review ledger: round 7 (incremental)", "2026-10-09T16:00:00")

# ---------------------------------------------------------------- the diff
orders(fixed=True)
repo(f2=True)
w("app/payments.py", PAYMENTS + """

    def void(charge_id: str) -> dict:
        return _post(f"/charges/{charge_id}/void", {})
""")
w("app/tests/test_create.py", """
    import sqlite3
    import unittest
    from unittest import mock

    from app import orders


    @mock.patch("app.orders.metrics.emit")
    @mock.patch("app.orders.payments.void")
    @mock.patch("app.orders.payments.charge", return_value={"id": "ch_1"})
    @mock.patch("app.orders.repo")
    class CreateTest(unittest.TestCase):
        def test_paid_order_is_reported_paid(self, repo, charge, void, emit):
            repo.cart_total.return_value = 40.0
            repo.insert_order.return_value = 7
            self.assertEqual(orders.create({}, {}, "u1")["status"], "paid")
            repo.set_paid.assert_called_once_with(7, "ch_1")
            void.assert_not_called()

        def test_unrecorded_payment_is_voided_and_fails(self, repo, charge, void, emit):
            repo.cart_total.return_value = 40.0
            repo.insert_order.return_value = 7
            repo.set_paid.side_effect = sqlite3.OperationalError("database is locked")
            with self.assertRaises(sqlite3.OperationalError):
                orders.create({}, {}, "u1")
            void.assert_called_once_with("ch_1")
            emit.assert_not_called()
""")
D = {}
D["a"] = commit("Void the charge when a paid order cannot be recorded\n\nset_paid failures were swallowed after a successful charge. Now the\ncharge is voided and the request fails; set_paid takes the write lock\nup front so its three writes commit together.", "2026-10-12T10:00:00")
repo(f2=True, retry_n=3)
D["e"] = commit("Retry transient 'database is locked' errors on order lookup\n\nThree replicas share the SQLite volume; lookups occasionally hit the\nlock and surface as 500s.", "2026-10-13T10:00:00")
repo(f2=True, retry_n=3, order=" ORDER BY id DESC", listing=True)
orders(fixed=True, listing=True)
server(listing=True)
D["c"] = commit("Add GET /orders (order history); newest-first search results", "2026-10-14T10:00:00")
rm("worker/import_legacy.py")
D["f"] = commit("Remove the one-off legacy import (migration finished)", "2026-10-15T10:00:00")

import json
(BASE.parent / "base-s2-hashes.json").write_text(json.dumps({"H": H, "ledger": LEDGER_C, "D": D}, indent=1))
print(git("log", "--oneline", "--reverse"))
print(git("status", "--short") or "clean")
