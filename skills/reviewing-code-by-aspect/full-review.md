# Full and incremental review

The flow, score bands and summary header for the two scored modes. The
severity rules, verification gate and principles in SKILL.md apply
throughout; this file adds what only a scored, ledgered review needs.

## Flow (full and incremental)

1. **Locate the ledger.** Default `docs/review/review.md` in the target
   repo. If it exists, its baselines, declared assumptions, user overrides
   and custom rubrics are all still in force; a full re-review starts from
   the ledger's assumptions and overrides — never re-scouts from zero — so
   two full passes calibrate identically. Apply the tidy tripwire
   (`ledger.md`) before dispatching anything.
2. **Select scope and aspects in one prompt.** Show the `aspects.md` menu as
   a numbered two-column list with core aspects pre-selected; invite
   toggles by number, "all", and custom aspects by name; ask the scope
   (whole repo default, or named paths). A custom aspect gets its ladder
   drafted on the spot in the same tier scheme. Echo the final list once
   for confirm-or-edit. **One confirmation** — a review is expensive enough
   to deserve one, and ceremony beyond it is waste.
3. **Plan scope per aspect.** Each aspect has its own baseline hash. No
   baseline → full pass for that aspect; baseline → diff since it. A run
   may mix both. A scoped run advances baselines only for what it reviewed;
   files outside a prior scope are unbaselined for that aspect; scoped
   scores are labeled with their scope wherever shown — a module's score
   is never presented as the codebase's.
4. **Choose the execution tier with the user, once.** Offer three:
   strongest-model fan-out (depth), strongest orchestrator with mid-tier
   reviewers (middle), inline single-agent (economy). Name the cost —
   fan-out multiplies tokens by the cluster count — and let the user trade
   missed-finding risk against quota; recommend depth for full reviews,
   never default to it silently. Settle the reviewer channel here too
   (where dispatch needs permission or is unavailable) and record the
   answer; re-asking each round trains the user to wave the review through.
   Independence is a separate axis: if this session authored the code,
   delegate to a clean-context reviewer regardless of diff size
   (`orchestration.md` › Reviewer independence).
5. **Scout once.** Read `docs/domain-context.md` first if it exists (written
   by `documenting-domain-context`): its owner-confirmed facts are the
   strongest evidence a declaration can cite; its `repo:` lines are
   the review's declared assumptions, restated with their line rather
   than re-derived; its module map names the core-path modules severity
   is placed against; a hazard is credited only when its line carries
   owner acceptance — a hazard the owner declined is filed as a finding
   that cites the line; and a contradiction between the file and the
   code is reported, never silently resolved either way. If it
   is absent, read the requirements and design documents the repo keeps
   (`docs/`, ADRs, specs) for the same facts — scale, trust model,
   external-party outcomes, invariants — and cite each one used by path;
   they are repo evidence, not owner confirmation. Then proceed and add
   one line to the presented summary — never the ledger (its `Context:`
   line stays the bare template value), never a question, never a gate:
   "No owner-confirmed context found — assumptions declared from the
   repository alone; scale, fee and trust severities are calibrated
   against defaults. `documenting-domain-context` (a short owner Q&A)
   recalibrates the next review." When the file exists,
   its invariants (§6) and every module's hazards and not-exercised lines
   (§7) become a **checklist the review answers line by line** in Declared
   assumptions — each invariant `held` / `violated at file:line` / `not
   reachable`, each hazard `credited` (owner accepted) / `filed as <ID>`
   (owner declined, or unruled and confirmed in code) / `not found`, each
   not-exercised operation named so reach answers can cite it. A listed
   line that no cluster adjudicated is a scope gap the summary names. One
   pass produces the declarations every aspect consumes:
   languages and house pattern per language, auth model, deployment model
   **with the scale the code runs at** (instances, tenants, throughput —
   what MEM/CPU/CON severities are judged against), consumed contract
   surfaces, generated/vendored exclusions, **domain facts** findings will
   rely on (who bears a fee and in what unit, whether an accepted request
   can stay pending, how long a token stays valid), the **mechanical
   sweeps** run with hit counts, and the operations enumerated for the
   journey table. Each declaration states the **weakest claim its evidence
   supports**: manifests prove the code *supports* a platform, not that it
   runs there — "assumed X; basis: repo ships k8s manifests (capability
   evidence only)", never a runtime asserted as fact. Never ask the user to
   fill a gap: declare the most defensible standard and proceed; overrides
   come later and persist.
6. **Review.** Fan out by cluster or run clusters inline
   (`orchestration.md`). Incremental aspects: re-check open findings whose
   files the diff touched (resolved / still open), carry untouched ones
   forward unchanged, add new findings from the diff only. A new finding
   that is the same distinct issue as an archived one **reopens that ID**
   (`reopened @hash`) — the ID names the defect, not the event of finding
   it, and a regression usually earns a TSQ cross-ref. **A fix re-review
   sweeps the whole enclosing unit** (function/class) as new code, never
   just the changed lines. **Every file in scope gets its own pass** — the
   reviewer keeps a checklist of files (diff-touched files in incremental
   mode) and confirms each was read before returning; a companion file
   (interface, config, migration, test) is not covered by reviewing its
   implementation.
7. **Verify, then merge mechanically.** Every proposed critical or major
   passes the verification gate below before it gets an ID; its tier is
   read off the severity table from the verified worksheet line. Dedup
   cross-referenced findings (one home aspect, one deduction), compute
   scores by the band table, update the ledger, present the summary. No
   model judgment in this step — that is what makes results reproducible.
8. **Stop.** Present the summary (worst aspect first) and end. No fixing,
   no second pass, no offer-loop. Fixes are a new task the user scopes
   against named finding IDs. Regenerate any HTML/JSON view that already
   exists beside the ledger — they are stale the moment the ledger changes
   (`ledger.md`). Recommend committing the ledger (a new ledger directory
   also gets `template/gitignore` as `.gitignore`, so derived views stay
   out of the repo); the skill itself never commits. When the fresh-eyes
   signals hold (`orchestration.md` › blind fresh-eyes pass), the summary
   carries that section's advisory line as written — it names the full
   pass's cost and a cheaper scoped option; "consider a blind review"
   alone gives the user nothing to choose between.

**Dirty working tree.** A scored review targets a commit — baselines are
reproducible only at a hash. If the tree is dirty, review HEAD and declare
the dirty/untracked files "uncommitted changes NOT reviewed". When the user
asks for uncommitted work, run it *provisional*: mark dirty-file findings
`provisional @uncommitted — re-verify at next commit` and advance no
baseline past HEAD. A baseline once recorded against a dirty tree makes its
dirty-listed files unbaselined — full re-check, not diff.

## Scoring

Per aspect, 0–10. **Severity sets the band; count refines within it:**

| Worst open finding | Score |
|---|---|
| none | 10 |
| minor only | 9 — flat; minors are listed and counted, never deducted |
| major | 6, −1 per additional major, floor 4 |
| critical | 3, −1 per additional critical, floor 0 |

Reading: **9–10** nothing structural (10 = nothing found, 9 = polish only)
· **4–6** real issues, schedule fixes · **≤3** do not ship this aspect.
Aspects that cap their own tier (no-critical floor 4, minor-only band 9)
encode how serious that aspect can get.

- **Minors never move the score** because their supply is unbounded — every
  codebase holds endless naming drift and magic constants, and each review
  samples a different handful. Deducting per minor would score which
  handful the reviewer picked. The aspect header still shows the count.
- **Widespread findings.** A finding (one issue, with its occurrence list)
  is *widespread* when it spans multiple modules or roughly a quarter of
  the files where the convention applies; a widespread major counts double
  (sets the band and deducts one more step → 5). Doubling never applies to
  criticals; on minors the label is descriptive. The finding states which
  level applied and why.
- **Scores are recomputed from all open findings, old and new** — an
  incremental review still scores the codebase, not the diff.
- The scale stays 10. A 100-scale adds no resolution (the measurement is
  band + count) and invites chasing phantom 3-point differences.

**Summary header, in order:** the worst aspect and its score (a review is
as good as its weakest aspect), then the full per-aspect table in catalog
order (never sorted by score — fixed rows let two reviews be compared
line-for-line), then the average *only* as a trend. Never lead with the
average: fourteen 10s and one 2 average to 9.5 on a codebase that must not
ship.
