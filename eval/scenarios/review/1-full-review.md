# Scenario 1: full review

Fixture and answer key: [`fixture.md`](fixture.md).

**Setup detail — dirty tree:** after committing the fixture, leave ONE
uncommitted edit in place (append a harmless helper to `app/config.py`).
This exercises the dirty-working-tree rule: the review must target HEAD and
declare the dirty file unreviewed.

**Prompt** (identical for both arms; skill arm prepends "Read
skills/reviewing-code-by-aspect/SKILL.md first and follow it"; control
arm prepends "Do NOT load or read any skill, convention guide, or AGENTS.md
from this environment"):

> Review this repository's code quality. I want a concrete, documented
> result I can act on — including scores. Cover at least: correctness, error
> handling, security, memory/resource behavior, test quality, and code
> style. Put the result somewhere durable.

**Checks** (PASS/FAIL per run):

1. No source file modified by the run — review only (git status shows
   nothing beyond the review doc and the pre-existing uncommitted setup
   edit, which the run must not commit, revert, or extend).
2. A review document exists at `docs/review/review.md` (or the run asked
   nothing and still produced a durable doc) containing per-aspect scores
   AND findings with file:line — not scores alone, not findings alone.
3. Doc records the reviewed commit hash (per-aspect or global baseline).
4. Seeds 1–5 found with tier critical (allow LOG seed 7 at major; allow
   seed 4 at major when the doc explicitly argues non-enumerable ids under
   the SEC ladder's demonstrated-path clause); at most one seed missed
   overall.
5. Zero decoys D1–D5 reported as findings.
6. Score arithmetic reproducible: for at least two aspects, recompute the
   score from the doc's own open findings via the band table and match.
7. FMT/naming issue (seed 6) reported as ONE finding with occurrence list,
   not per-file findings; aspect score for it exactly 9 (minor-only band —
   minors are counted, never deducted).
8. Headline/summary leads with the worst aspect, not an overall average.
9. Declared assumptions present (detected pattern and auth model, each with
   evidence), and the deployment-model declaration is worded as an
   assumption with its evidence basis — the fixture's sidecar manifests
   prove the code *supports* that platform, not that it runs there;
   asserting the runtime platform as fact is a FAIL. Likewise the
   house-pattern standard must derive from in-repo evidence (dominant
   pattern, in-repo configs/docs); binding a convention set from the
   reviewing agent's own environment (e.g. installed skills) without a user
   override is a FAIL.
10. The run ends after presenting the review — no unprompted fixing, no
    offer-loop of repeated re-review.
11. Dirty-tree handling: the doc declares the uncommitted `app/config.py`
    edit as dirty/unreviewed, the recorded baseline is HEAD's hash, and no
    finding is anchored to the uncommitted content.
12. The aspect-selection prompt also asks the review scope (whole repo
    default vs named modules/paths) within the same single confirmation —
    no extra ceremony round.
13. The execution-mode offer names the cost/quota trade-off and includes at
    least one economy option (mid-tier reviewer agents or inline
    single-agent) alongside the recommended fan-out.
14. The ledger follows `template/review.md`: section names and order match
    (Summary, Review scope, Declared assumptions, User overrides, Open
    findings, Credited as intentional, Resolved findings, History); the
    summary-table rows and the open-findings aspect sections are in catalog
    order (never sorted by score), and each aspect header carries
    `<score>/10 · <n> open` behind a `---` rule.
15. Mechanical sweeps recorded and effective: Declared assumptions carry a
    "Sweeps run" entry naming at least the raw-identifier-splice sweep with
    its pattern and scope, AND both planted splices (P1a obvious, P1b
    obscure — see setup plants below) are surfaced. Missing P1b is a FAIL.
16. Journey defect (P2, authorize-without-capture recorded as paid)
    reported as critical or major with the cross-layer path named (caller
    omits field → model default → handler treats "authorized" as
    success). Crediting it on the strength of the narrating comment is a
    FAIL.
17. Init-only DDL (P3) reported under Contract & compatibility at or above
    major, naming the missing delivery path to a live database.
18. Verification gate: every critical or major carries concrete
    verification evidence (failing input / source→target path re-derived
    from the code); no aspect score counts a finding the doc marks
    candidate/unverified.
19. Domain-context contract: the fixture has no `docs/domain-context.md`.
    The presented summary carries the one-line advisory naming
    `documenting-domain-context`; the advisory is NOT in the ledger; the
    Review scope carries `Context: declared from code`; and no question
    about domain context, scale, or business facts was put to the user
    before the review ran (a gate is a FAIL).

**Setup plants for checks 15–17** (added to the seeded fixture): P1a — an
obvious raw SQL identifier splice (table name from a route param); P1b — an
obscure one (a column name concatenated in a small helper, reached through
two renamed hops); P2 — a three-layer external-state defect (caller omits
a `capture` field, model defaults it to authorize-only, handler records an
"authorized" response as paid, with a branch-narrating comment); P3 — DDL
mounted only under a container first-boot init directory with no migration
step, plus an `ALTER TABLE` a newer code path depends on.
