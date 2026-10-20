# Scenario 6: overlapping findings get linked by ID

Does an incremental review link two carried-forward findings that share a line, without merging them or re-checking
code the diff left alone?

Fixture: [`build_s6_fixture.py`](../../fixtures/reviewing-code-by-aspect/build_s6_fixture.py) writes `base-s6/`: the
fixing-scenario repo (its key is [`../fixing/fixture.md`](../fixing/fixture.md)) plus commit `4c470a2`, a health route
in `server.py` and a README line. LOG-001 (`reservations.py:28-30`) and CON-001 (`reservations.py:28`, `:36`) share
line 28 and do not name each other; LOG-002 and CMP-001 share no line with anything.

**Setup:** the fixture repo, unmodified.

**Prompt** (arms as in scenario 1):

> The repo has changed since the last review (see docs/review/review.md). Update the review.

**Checks** (PASS/FAIL per run):

1. Linked: LOG-001's `Cross-ref` names CON-001 by ID and CON-001's names LOG-001.
2. Not merged: both stay open under their own IDs, and the LOG and CON scores count both by the band table (LOG 5 and
   CON 6 unless the run adds a verified LOG or CON finding, in which case recomputed with both still counted).
3. No false links: LOG-002 and CMP-001 gain no ID link to LOG-001 or CON-001 (LOG-001's aspect-level `CMP` cross-ref
   may stay).
4. Carried forward: apart from the new links, LOG-001, CON-001 and LOG-002 keep their tier, occurrence lines and
   evidence text.
5. No source file modified.
