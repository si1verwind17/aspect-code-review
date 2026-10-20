#!/usr/bin/env python3
"""Scenario-6 fixture: overlapping findings get linked by ID.

Builds the fixing-reviewed-findings fixture (its ledger holds LOG-001 and
CON-001, which share `stockroom/reservations.py:28` but do not name each
other) into base-s6/ beside this file (gitignored), then adds one commit
that leaves both findings' code alone: a health route in server.py and a
README line. An incremental review over that commit carries both findings
forward and must link them. Stdlib only.
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "fixing_fixture", HERE.parent / "fixing-reviewed-findings" / "build_fixture.py")
fx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fx)
fx.OUT = HERE / "base-s6"

HEALTH = '''\
    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok"})
        return self._send(404, {"error": "NotFound"})

    def do_POST(self):'''


def main():
    fx.main()
    server = fx.OUT / "stockroom" / "server.py"
    text = server.read_text()
    assert text.count("    def do_POST(self):") == 1
    server.write_text(text.replace("    def do_POST(self):", HEALTH))
    readme = fx.OUT / "README.md"
    readme.write_text(readme.read_text() + "\nHealth check: `GET /health`.\n")
    fx.git("add", "-A", date="2026-10-02T09:00:00+00:00")
    fx.git("commit", "-q", "-m", "server: health route", date="2026-10-02T09:00:00+00:00")
    print(f"head {fx.git('rev-parse', '--short=7', 'HEAD')}")


if __name__ == "__main__":
    main()
