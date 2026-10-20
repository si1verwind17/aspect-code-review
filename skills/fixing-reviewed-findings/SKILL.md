---
name: fixing-reviewed-findings
description: >-
  Use when asked to fix findings from a code review ledger
  (`docs/review/review.md`) by ID or tier — "fix LOG-009", "fix the
  criticals", "work through the open findings" — so that each fix is
  re-reviewed before it lands. Covers which findings travel together, the
  fix branch and its commits, contract changes, the clean-context
  re-review, and when to stop. Keywords: fix findings, remediation, fix
  branch, re-review, review ledger.
---

# Fixing reviewed findings

Turn named findings from a `reviewing-code-by-aspect` ledger into code
changes, then let a clean-context incremental review judge them. This
session writes code; **only the review decides what is resolved**. It
never marks a finding resolved, never edits a finding's text, and never
stamps a hash into the ledger by hand: the author grading its own fix is
the bias the review's independence rule exists to remove.

## 1. Gather the fix group before editing

A finding named alone is rarely alone. Before touching code, list every
**open** finding that cites a file:line range overlapping one the target
cites, or that names the target in its `Cross-ref` (or is named in the
target's). Read each one's evidence and fix direction.

**Linked findings are in scope by default** — fix them in the same change.
Leave one out only when its fix is independent of the target's (another
code path, no shared invariant), and say which and why in the report.
Fixing one ID while a linked finding sits in the same statement leaves the
code wrong in a way the ledger already names — an end-date clamp that
still lets an explicit date revive an already-ended rule. Noticing the
link and calling it "a separate finding" is the failure this rule is for.

Unlinked findings noticed along the way are not fixed; the next review
picks them up.

## 2. Branch

Start a new branch from the default branch (`fix/<IDs>`) and record the
base hash. **One fix branch per ledger at a time:** every review edits
`docs/review/review.md`, so two open fix branches conflict on merge, and
the second was reviewed against a ledger that lacked the first one's
resolutions.

## 3. Fix

Change what the group's evidence calls for: each finding's failing input
must no longer fail.

**Contract changes are allowed and announced.** A fix may need a new error
code, a status mapping, a schema or migration change, or a changed public
behaviour. Make it when the finding cannot be fixed without it, and tell
the user each one: what changed and why the fix needed it. Where you chose
between defensible options (409 or 422; clamp or relax the constraint),
name the choice and the alternative. These decisions outlive the finding,
and two careful fixers often decide them differently; the user must see
them in the report, not discover them in a diff. Editing a migration that
may already be applied is a contract change.

## 4. Commit, then hand off to a clean reviewer

Commit the fix on the branch: a scored review targets a commit, and the
ledger cites fixes by hash. Then run the incremental review in a **fresh
agent with none of this session's context**. Brief it only to run
`reviewing-code-by-aspect` in incremental mode on the repository at the
head commit, named by its hash; the branch name carries the IDs. Do not
pass the target IDs, the fix's intent or your reasoning: the review re-checks open findings in touched files on its own,
and a reviewer told what the fix meant to do grades the intent instead of
the code.

When it returns, commit its ledger change as a separate commit,
`review @<fix-hash>: <IDs resolved>`, so each fix and the review that
judged it stay distinct in history.

**No way to start a clean agent → stop after the fix commit** and tell the
user to run the incremental review in a fresh session. Never review in
this session as a fallback; a fix loop that grades itself has nothing
independent left in it.

## 5. Pass, or one more round

A round **passes** when the review marks every ID in the fix group
resolved and adds no critical or major finding on lines this branch added
or changed. Otherwise fix only what failed — a group ID still open, or a
critical or major the fix itself introduced — and repeat steps 3–4: a new
fix commit, a new review, a new ledger commit. A defect the review newly
finds on lines the branch left alone predates the fix, even inside an
edited function: report it, never chase it. New minors are reported,
never chased.

**At most two rounds.** After a second failed round, stop on the branch
and report what is still open and why. Every review of a fix finds
something; a loop that runs until the review is silent never ends, which
is the loop the review-only skill exists to break. Say in the report that
the cap was reached — it is never applied silently.

## 6. Hand back the branch

Never push, open a pull request or merge; that is the user's call. Report:

- the fix group, and any linked finding left out with the reason;
- each contract change, with why it was needed and the alternative;
- each round's fix hash and what its review resolved or found;
- what is still open.

Advise the merge: **fast-forward or a merge commit — never squash, and no
rebase after a review commit.** The ledger cites fix commits by hash; a
rewritten hash leaves its History rows and `found @` lines pointing at
commits that are not on the default branch.

## Common mistakes

- **Marking a finding resolved** or rewording it in the fix session.
- **Leaving a linked finding** in the same code because it has its own ID.
- **Briefing the reviewer** with the targets or what the fix intended.
- **Uncommitted fixes handed to review** — there is no hash to cite.
- **Squash-merging** a reviewed fix branch.
- **Chasing the fix's own minors** round after round.
