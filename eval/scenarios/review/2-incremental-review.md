# Scenario 2: incremental re-review

Fixture and answer key: [`fixture.md`](fixture.md).

**Setup:** fixture repo plus a ledger from a prior scenario-1-style run
(hand-authored from the answer key if needed); then a diff that (a) fixes
seed 1, (b) touches the file of seed 3 without fixing it, (c) adds one new
defect (unpaginated list endpoint — CPU major), (d) leaves seed 5's file
untouched, (e) reintroduces a defect the ledger's archive records as
resolved (hand-author one one-line archived finding for this — tier it per
the aspect ladder, and pick a major-tier defect shape: a silent-swallow
shape re-derives to critical on reopen and cancels check 3's expected ERR
rise), and (f) removes the code referenced by one credited-as-intentional
entry (hand-author that entry too). Fixture rules learned in round 6: the
archive line for (e) must name the SAME operation the diff reintroduces,
and the reintroduced shape must stay MAJOR on re-derivation (a logged-and-
retried failure, a wrong default) — round 7's `return None` swallow in
`charge()` re-derived to critical 3/3 and cancelled check 3's ERR rise
(a "webhook timeout" archive line against a `charge()` regression makes
every careful reviewer mint a new ID); the enclosing-unit plant F2 for
check 10 must sit in a DIFFERENT function from the seed-1 fix (in the
same function, reviewers defensibly keep seed 1's ID open with a rebuilt
body instead of resolving it, which collapses checks 1, 7 and 10 into
one modelling call). The prior ledger also carries the hygiene and
advisory plants named in checks 8–9.

**Prompt** (arms as above):

> The repo has changed since the last review (see docs/review/review.md).
> Update the review.

**Checks:**

1. Seed 1's finding marked resolved; seed 3's finding still open (re-checked,
   not duplicated under a new ID); seed 5 carried forward unchanged, its file
   not re-reviewed.
2. New finding added for the unpaginated endpoint (under CPU or memory,
   whichever fits the ledger's selected aspects) with input/scale/heat
   evidence.
3. Scores recomputed from ALL open findings (whole-codebase), and ERR score
   rises per the band arithmetic after seed 1's resolution.
4. Per-aspect baseline hashes advance to the new commit.
5. No source file modified; run terminates after the summary.
6. The reintroduced defect (e) reopens its archived ID — back in Open
   findings with `reopened @hash` and a rebuilt evidence body (its tier is
   re-derived from current evidence and may differ from the archived line
   when argued), counted in its aspect's score — not filed under a new ID;
   and its old `resolved @hash` archive line is gone (open and resolved at
   once is a FAIL).
7. Ledger hygiene: seed 1's resolved finding is archived as a single line
   (ID, severity, title, files, resolved @hash — no full body), and the
   credited-as-intentional entry whose code the diff removed (f) is
   deleted.
8. Snapshot, not changelog: the Summary describes THIS review only — prior
   rounds' narrative paragraphs planted in the fixture are removed, not
   appended to or preserved; resolved findings' bodies leave their aspect
   sections; the Open-findings header hash advances. A preserved stale
   narrative or a "still open" claim beside its own resolution is a FAIL.
9. Fresh-eyes advisory: with the fixture History showing many incremental
   rounds since the only full pass, the presented summary carries a
   one-line advisory recommending a blind full review that names its cost
   and at least one cheaper scoped option; the advisory does NOT appear in
   the ledger, and the run does NOT launch a blind pass itself.
10. Enclosing-unit sweep: the second defect F2 planted in the fix commit
    is reported at its ladder tier (any ID). Missing F2 is a FAIL.
11. Verification gate: every critical or major in the updated ledger
    carries concrete verification evidence; candidate/unverified findings
    are not counted in any score.
12. Assumptions reuse: the Declared assumptions block is carried forward
    from the prior ledger, amended only where evidence changed (an
    evidence-based correction of a planted false declaration counts as a
    PASS) — not re-scouted from zero or rewritten; the block header keeps
    the prior `scout pass @<hash>` (an appended `amended @<hash>` is fine) —
    re-stamping it to HEAD without a re-scout is a FAIL.
13. Sweep before reconcile: the run's NOTES (or the dispatched briefs it
    records) show each reviewer received declarations first and its
    aspects' open findings only after returning a fresh sweep — a brief
    that lists the open findings alongside the initial review instructions
    is a FAIL. An inline run (no reviewer dispatched) has no brief to
    inspect: grade N/A and score that rep out of one fewer check.
14. TSQ mutation executed: the prior ledger carries a TSQ candidate
    ("<risky path> untested — candidate, unverified") whose named mutation
    passes the suite today; the fixture's test command works
    (`python3 -m unittest`). PASS = the run applied the mutation in a
    scratch copy, ran the suite, recorded the result, and either promoted
    the candidate to a verified major or refuted it with a red run; the
    fixture tree is left unmodified. Settling the candidate either way
    without a recorded run is a FAIL.
15. Tidy on read: the fixture Summary exceeds 40 lines of round narrative
    and one Declared-assumptions bullet carries an "amended @hash, the
    earlier declaration was wrong" history. PASS = output Summary ≤ ~40
    lines and that bullet restated as a current fact (no change
    narrative), with every finding ID that existed before still present,
    the User overrides section byte-identical, and no tier changed by the
    tidy itself.
