# Scenario 2: update mode after a change

Fixture and answer key: [`fixture.md`](fixture.md).

**Setup:** scenario-1 fixture plus a completed context file (hand-authored
from the answer key), then a diff that (a) adds a second external party
(a notification webhook) with a retry loop, (b) changes the manifest to
`replicas: 1` (now agreeing with the owner), (c) removes the metrics
swallow that F10 credits, and (d) touches nothing else. Owner (judge)
answers: webhook delivery failures are retried three times then dropped
— accepted hazard, consequence "user misses one alert".

**Prompt:** "The code changed since docs/domain-context.md was written.
Bring it up to date."

**Checks:**

1. Only the new party (a) and the removed hazard (c) are raised with the
   owner; F1–F7 are not re-asked. Re-asking the open unknowns F8 and F9
   once is allowed — the open-unknowns list exists for a later pass to
   ask from.
2. The webhook is added under the owning module's *External parties*
   (or **Shared** if both core modules call it) with its retry/drop
   semantics (repo provenance acceptable — the mechanics are code facts)
   and under that block's *Hazards* with the owner's consequence and
   `accepted by owner (date)` provenance.
3. F10's hazard entry is removed (the code it credited is gone), not
   struck through or annotated.
4. The replicas fact keeps `owner` provenance and is restated as a fact —
   no "previously the manifest said 3" narrative anywhere in the file.
5. Section 8's commit hash and confirmation date advance; open unknowns
   still list F8 and F9; the module map's rows, paths and roles are
   unchanged (a purpose cell may gain a clause for the new party) and the
   map was not re-asked as a batch.
6. Run ends after presenting the diff of the file; nothing committed.
