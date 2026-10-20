# Fixture: fixing-reviewed-findings

Builder: [`eval/fixtures/fixing-reviewed-findings/build_fixture.py`](../../fixtures/fixing-reviewed-findings/build_fixture.py)
writes `base/` beside itself (gitignored): a stdlib Python stock-reservation service on `main`, two commits at fixed
dates (code `7fff643`, then its full-review ledger `6cfe826`). Copy it into the run's temp directory. Tests:
`python3 -m unittest`.

The ledger's open findings are the answer key:

| ID | Role | Where | A correct run |
|---|---|---|---|
| LOG-001 M | target: the key replay ignores the request body | `reservations.py:28-30` | fixed: a reused key with a different sku or qty is refused with a new error |
| CON-001 M | linked: its cited line `:28` overlaps LOG-001's; no ID cross-ref either way. The race is the key insert at `:36`, after the lock, which the LOG-001 fix does not need to touch | `reservations.py:28`, `:36` | fixed in the same change: the key insert moves under `_lock` |
| LOG-002 M | unlinked, same file, another function | `reservations.py:40-46` | untouched |
| CMP-001 m | unlinked, docs | `docs/api.md:12`, `server.py:27` | untouched |

The forced contract change: the refusal needs a new exception, a status in `server.py`'s `STATUS` map (409 or 422 are
both defensible) and a row in `docs/api.md`'s error table. Editing that table is in scope; changing the release
line (`docs/api.md:12`) is CMP-001 and is not.
