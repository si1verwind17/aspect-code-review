# Scenario 4: quick mode — one PR, tiered, unscored

Fixture and answer key: [`fixture.md`](fixture.md).

**Setup:** the scenario-1 fixture committed clean, plus a feature branch
`feature/refunds` (3 commits, ~120 changed lines across 4 files) that
implements a `POST /orders/{id}/refund` endpoint against a plan file
`docs/plans/refunds.md`. The plan states: refunds require the order to be
`paid`; partial refunds are allowed up to the paid amount; a refund emits
a `RefundIssued` event. Plants in the branch: Q1 — the state check accepts
`shipped` as well as `paid` (REQ major: visible deviation, uncalled-out);
Q2 — the amount check is `amount <= order.total` where the plan says paid
amount and a partially-refunded order's paid amount is lower (LOG
critical: silent over-refund on a reachable path); Q3 — the event publish
is wrapped in `except Exception: log.debug(...)` (ERR critical: silent
failure of a consumed contract); Q4 — the new test file asserts on the
HTTP status only (TSQ minor — happy-path bias; NOT major, the risky path
Q2 has a named failing input from LOG already and TSQ cross-refs it);
Q5 — a helper renamed in commit 2 but its `__init__.py` re-export not
updated (companion-file plant: the enclosing-unit and per-file checklist
rules are what find it — CMP major, breaks importers). Decoy QD1: the
refund handler validates nothing itself because the router-level schema
validator covers the body (journey-not-call-site). No ledger exists.

**Prompt** (arms as in scenario 1):

> Review the `feature/refunds` branch against `main` before I open the PR.
> The plan is in docs/plans/refunds.md. I just want the findings.

**Checks** (PASS/FAIL per run):

1. No source file modified; no `docs/review/review.md` created; the run
   ends after the findings list (no fix offer, no second pass).
2. Output is a findings list worst-tier first with `ABBR · tier · title ·
   file:line · evidence`; **no per-aspect scores and no overall score or
   average anywhere** — a number is a FAIL.
3. Q2 and Q3 reported at critical with a concrete failing input /
   swallowed-path evidence; Q1 reported under REQ with the plan sentence
   quoted; Q5 reported (any ID) at major, or at critical when its
   worksheet line records the startup failure as signal none (the
   severity table puts process residue with no signal at critical).
4. Q4 not reported as a counted major — at minor, or carried as evidence
   inside the LOG finding, or mentioned untiered when TSQ was not selected
   (TSQ is opt-in and quick mode runs the core set), or listed as an
   unverified TSQ candidate when the suite cannot run (a named-but-unrun
   mutation is a candidate by the TSQ ladder); QD1 not reported.
5. A one-line verdict closes the output (`N critical, M major open`); no
   "strengths" section, no praise paragraph.
6. Candidates, if any, listed separately from findings and not in the
   verdict count.
7. Every one of the 4 changed files is named in the output as reviewed
   (a checklist line or a per-file mention) — 3/4 is a FAIL.
8. Each finding carries a one-line fix direction, and none contains a
   patch or code block longer than one line.
