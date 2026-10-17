# aspect-code-review

Agent skills for code review that ends in a scored, documented result instead of an endless fix-as-you-go loop. Each
skill is a plain-Markdown `SKILL.md` in the open [Agent Skills](https://agentskills.io) format, usable from Claude
Code, GitHub Copilot, Cursor, Codex, Antigravity CLI and any other agent that reads it.

What these skills add, compared with asking an agent to "review this":

- **Review by aspect.** You pick the aspects (logic, error handling, security, concurrency, contracts and more); each
  has a severity ladder, an evidence requirement, and a list of things it must not flag.
- **Scores you can reproduce.** Every aspect gets a 0–10 score computed from its open findings by fixed arithmetic,
  so "improve the score" means "resolve these named findings".
- **A ledger that persists.** Findings, declared assumptions and per-aspect baselines live in
  `docs/review/review.md`; the next run reviews only what changed and carries the rest forward.
- **Review only.** The skill never edits code. Fixing is a separate task you start and scope.

## Demo

A full review of a Kotlin booking service, with its domain context, is in [`demo/`](demo/). It is followed by five
fix commits, each re-reviewed incrementally. Open the
[rendered review page](https://si1verwind17.github.io/aspect-code-review/) and drag its timeline to see what each
fix resolved and how the scores moved, or read the [ledger](demo/booking-service/docs/review/review.md) it is
generated from.

## Install

**Claude Code**

```
/plugin marketplace add si1verwind17/aspect-code-review
/plugin install aspect-code-review@aspect-code-review
```

**GitHub Copilot, Cursor, Codex, Antigravity CLI and others,** via GitHub CLI:

```
gh skill install si1verwind17/aspect-code-review
```

**Anything else:** copy the `skills/<name>/` directories into your agent's skills folder.

No prerequisites for the skills themselves. Rendering the ledger to HTML or JSON needs Node 18 or later.

## Skills

- [`reviewing-code-by-aspect`](skills/reviewing-code-by-aspect/SKILL.md): three modes. **Full** audits the whole repo
  or named paths and writes the scored ledger; **incremental** re-reviews the diff since each aspect's baseline;
  **quick** reviews one diff or PR and returns tiered findings with no score and no ledger.
- [`documenting-domain-context`](skills/documenting-domain-context/SKILL.md): optional, runs only when you ask.
  Writes down what the code cannot say to `docs/domain-context.md`, through a short Q&A with you. See
  [Domain context](#domain-context-optional) below.

## Aspects

A review covers the six core aspects by default; you add opt-in aspects by name or number when the review asks you
to confirm its scope, or name a custom aspect and the review drafts its severity ladder on the spot.

| Aspect | Default | What it checks |
|---|---|---|
| Logic correctness (LOG) | core | The code does what its names, types, tests and docs say it should |
| Error handling (ERR) | core | Every plausible failure is propagated, handled or deliberately ignored, never silently lost |
| Security (SEC) | core | Untrusted input is validated before it reaches anything dangerous; authn/authz holds end to end |
| Code pattern (PAT) | core | New code follows the codebase's own established patterns |
| Concurrency safety (CON) | core | Correct results under concurrent requests, jobs and replicas |
| Contract & compatibility (CMP) | core | APIs, events, schemas and migrations don't break the systems that consume them |
| Logging (LGG) | opt-in | An operator can follow a failing request through the logs |
| Memory (MEM) | opt-in | The process doesn't degrade over time: caches, buffers and connections are bounded |
| CPU (CPU) | opt-in | Per-operation cost at the scale the code actually runs at |
| State discipline (STA) | opt-in | State lives where the deployment model allows (e.g. nothing in process memory across replicas) |
| Testable code (TST) | opt-in | Business rules can be exercised without standing up the whole system |
| Test quality (TSQ) | opt-in | Risky paths have tests that would fail if the behavior broke |
| Type & null safety (TYP) | opt-in | The type system is used to rule out invalid states |
| Readability & maintainability (RDB) | opt-in | The next person can change this code safely |
| Format consistency (FMT) | opt-in | Naming and surface style are consistent within each language |
| Requirements alignment (REQ) | opt-in | The code matches the plan, ticket or spec it was written for (picked automatically in a quick review when one is given) |

Each aspect's severity ladder, evidence requirement and suppression list are in
[`aspects.md`](skills/reviewing-code-by-aspect/aspects.md).

### Scoring

Every finding gets a severity from three facts recorded with it, so two reviewers reading the same code reach the
same tier: who can reach the failing path, what it leaves behind, and whether anyone is told.

| What the failure leaves behind | Nobody is told | The caller or an operator is told |
|---|---|---|
| Wrong or missing state outside the process (data, money, a queue), or the service down | critical | major |
| A wrong or failed response, state intact | major | major |
| Nothing (structure, hygiene) | minor | minor |

A path no existing caller can take under the declared deployment model is minor whatever it leaves behind. Every
critical or major must survive an independent attempt to refute it before it counts.

Each aspect then scores 0–10 from its open findings by fixed arithmetic:

| Worst open finding | Score |
|---|---|
| none | 10 |
| minor only | 9 (minors are listed and counted, never deducted) |
| major | 6, −1 per additional major, floor 4 (a major spread across several modules counts twice) |
| critical | 3, −1 per additional critical, floor 0 |

Read it as: **9–10** nothing structural, **4–6** real issues to schedule, **≤3** do not ship this aspect. The summary
leads with the worst aspect; the average across aspects is shown only as a trend.

## Domain context (optional)

A review can only see the code. Without context it calibrates severity against defaults, and says so in its summary.
Recording domain context first makes the review's severities fit your system:

- **Scale:** a cache or an unpaginated query is critical or harmless depending on real throughput and data size.
- **Trust model:** where authentication actually happens decides whether a missing check is a finding.
- **External parties:** what a payment provider or other service can really return (a pending result, a request it
  may never act on) is where most silent-failure bugs hide.
- **Accepted hazards:** a risk you have knowingly accepted is credited instead of being reported again in every
  review.

The cost is your time. The skill drafts everything it can from the code and documents first, then asks you only what
the code cannot answer: two rounds of questions (at most 11 in total), then an optional list of up to 8 observations
you can answer by number or ignore. It is worth it before a full review you intend to act on, or when a review
summary says its assumptions were declared from the repository alone; skip it for quick PR reviews. Ask for it in
plain words, for example:

> Before we review this repo, write down the domain context for the reviewer.

## Use

Ask in plain words and the agent picks the matching skill from its description:

> Review this repository's code quality and give me scores I can track.

> Re-review since the last review.

> Review the `feature/refunds` branch against main before I open the PR.

## License

MIT, see [`LICENSE`](LICENSE).
