# Evaluations: aspect-code-review

Each scenario is one file under [`scenarios/`](scenarios/): its prompt and checks, pointing at the fixture and
answer key it shares with the skill's other scenarios (`fixture.md` in the same folder). Fixture builders and judge
keys live under [`fixtures/`](fixtures/). Start a new scenario from [`template.md`](template.md).

A single passing run proves a skill *can* work; only repetition proves it works *reliably*, and only a control arm
proves it changes anything.

## Protocol

- **Two arms.** Control: a fresh agent gets the scenario with the skill NOT loaded. Skill arm: identical but with the
  skill loaded. A check the control arm already passes consistently is dead weight: cut or sharpen that rule.
  Control prompts MUST explicitly forbid loading any skill or convention guide from the environment, because agent
  harnesses auto-discover skills and a control that silently reads the skill under test measures nothing. Check
  that control outputs don't echo the skill's distinctive vocabulary before trusting the arm.
- **Reps.** 3 per arm on Sonnet; an Opus rep is an optional spot check. Single runs lie; consistency across reps is
  the signal.
- **Independent grading.** A fresh judge grades each run against the checks and the answer key, never the session
  that authored the skill. Runners never see `fixture.md`, the builders or the keys.
- **No user in the loop.** Runners are told that no user is reachable: they write each prompt they would have shown
  into their report and proceed with the option they would recommend; judges grade those written prompts.
- **When to run.** After any substantive edit (skill arm; control too if checks changed) and when the underlying
  model changes.
- **Pending validation.** A substantive edit not yet benchmarked goes under **Pending validation** below: skill@hash,
  one line on what changed, which scenario will validate it. Delete the entry when a run validates it.
- **Latest result only.** **Latest results** keeps one row per scenario and arm: the latest measured result for the
  skill as it stands. A new run replaces its row; intermediate attempts are not kept (git history has them). Notes
  may name a residual miss, never a past score.
- **Real misses become checks.** When a skill-loaded agent gets something wrong in real use, add that case as a
  failing check first; the skill edit must flip it.

## Scenarios

### reviewing-code-by-aspect

| Scenario | What it tests |
|---|---|
| [1](scenarios/review/1-full-review.md) | a full review: seeds found at the right tier, decoys suppressed, reproducible scores, the ledger's shape |
| [2](scenarios/review/2-incremental-review.md) | an incremental re-review: resolve, carry forward, reopen, tidy, assumptions reused |
| [3](scenarios/review/3-render-ledger.md) | rendering a ledger to HTML for people |
| [4](scenarios/review/4-quick-pr-review.md) | a quick review of one branch: tiered findings, no score, no ledger |
| [5](scenarios/review/5-trigger.md) | a plain review request loads only the review skill |
| [6](scenarios/review/6-link-overlapping.md) | an incremental review links carried-forward findings that share a line |

### documenting-domain-context

| Scenario | What it tests |
|---|---|
| [1](scenarios/domain-context/1-first-run.md) | a first run: evidence-led interview with a simulated owner, provenance, scoped documents |
| [2](scenarios/domain-context/2-update-mode.md) | update mode after a change: only what changed is re-asked |
| [3](scenarios/domain-context/3-foreign-file.md) | a foreign file already at the output path |

### fixing-reviewed-findings

| Scenario | What it tests |
|---|---|
| [1](scenarios/fixing/1-fix-linked-finding.md) | a named finding fixed with its linked finding, on a branch, re-reviewed by a clean agent |

## Pending validation

None.

## Latest results

`Skill@` is the commit whose skill content was evaluated. Hashes dated 2026-10-17 refer to development history
squashed into this repository's first commit; they do not resolve here.

### reviewing-code-by-aspect

| Scenario | Skill@ | Model | Reps | Result | Notes |
|---|---|---|---|---|---|
| 1 | draft | Sonnet | 3 | 52/57 | all inline. Residual: no rep's written execution-mode offer names the cost trade-off (check 13, 0/3); one rep skipped the scope question (check 12); one rep dropped the `---` rules between aspect sections (check 14) |
| 2 | draft | Sonnet | 3 | 41/42 | check 13 N/A in every rep (all inline); one rep's fresh-eyes advisory named neither the cost nor a cheaper option (check 9) |
| 3 | 72be6d1 | Sonnet | 3 | 24/24 | every rep ran the skill's script; at the older History row the page shows that review's own changes, not the latest open list |
| 4 | 4199e31 | Sonnet | 3 | 24/24 | the suite cannot run on the host; Q4 lands as an unrun-mutation candidate, as checks 3–4 allow |
| 5 | f34e692 | Sonnet | 3 | 3/3 | only `reviewing-code-by-aspect` loaded |
| 6 | draft | Sonnet | 3 | 15/15 | control 12/15: links 0/3. Every rep ran `link_findings.mjs` |

### documenting-domain-context

| Scenario | Skill@ | Model | Reps | Result | Notes |
|---|---|---|---|---|---|
| 1 | cfed2c6 | Sonnet | 3 | 35/48 | payments fixture. Residual: F9 never asked; unprovenanced short lines; F1 cited to code, not the README (2/3); map sent as prose (1/3); OVERVIEW's cadence offered after scoping (1/3) |
| 2 | — | — | — | not run in this repository | |
| 3 | — | — | — | not run in this repository | |

### fixing-reviewed-findings

| Scenario | Skill@ | Model | Reps | Result | Notes |
|---|---|---|---|---|---|
| 1 | draft | Sonnet | 3 | 18/18 | control 3/18 (scope passes unaided; linked finding, branch, commit, clean review, hand-back 0/3). Every reviewer was briefed by hash; the branch name still shows the IDs to a reviewer who lists branches |
