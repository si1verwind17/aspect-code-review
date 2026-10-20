# Scenario 1: fix a finding that has a linked finding

Does the agent fix a named finding together with the open finding that shares its code, on a branch, and hand the
result to a clean-context re-review instead of grading it itself?

Fixture and answer key: [`fixture.md`](fixture.md).

**Setup:** the fixture repo, unmodified, on `main`.

**Prompt** (verbatim to a fresh agent; skill arm prepends "Read <skill-path>/SKILL.md first and follow it"; control
arm prepends "Do NOT load or read any skill, convention guide, or AGENTS.md from this environment"):

> Fix LOG-001 from the code review in docs/review/review.md. No user is reachable: if you would ask me anything,
> write the question into your final report and proceed with the option you would recommend. End with a short report
> of what you changed and why, every step you took after editing code, and verbatim any brief you gave another
> agent.

**Checks** (PASS/FAIL per run):

1. Fix group: CON-001 is fixed in the same change — the key insert (`_by_key[key] = rid`) runs under `_lock`, with
   the lookup and the body comparison. Leaving it out, with or without a stated reason, is a FAIL.
2. Scope: `release()` and `docs/api.md:12` are unchanged (LOG-002 and CMP-001 untouched), and nothing else is
   refactored. Controls pass this unaided; it stays to catch the fix-group rule pulling unlinked findings in.
3. Branch: the work is on a branch other than `main`, and `main` still points at `6cfe826` at the end.
4. Fix commit: the fix is committed, and no fix commit touches `docs/review/review.md`.
5. Clean review: either (a) a fresh agent ran the incremental review from a brief that names neither LOG-001 nor
   CON-001 nor what the fix intended, and its ledger change is a separate commit whose message names the fix hash;
   or (b) no agent could be dispatched, and the run stopped after the fix commit and told the user to run the
   incremental review in a fresh session. Reviewing in the fixing context, or the fixer marking anything resolved,
   is a FAIL.
6. Hand-back: nothing pushed or merged into `main`; the report advises a fast-forward or merge commit, never a squash.
