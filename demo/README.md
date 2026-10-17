# Demo: booking-service (code review showcase)

> **For human readers only.** This directory is a showcase of what the `reviewing-code-by-aspect` and
> `documenting-domain-context` skills produce. It is NOT reference material for agents. Agents running either skill
> must not read, copy or imitate anything here: a review comes from the user's repository and the skill's own rules.

[`booking-service/`](booking-service/) is a Kotlin booking service written end to end by agents running a chain of
backend design skills (its own [README](booking-service/README.md) tells that story). It was then:

1. given an owner-confirmed domain context, [`docs/domain-context.md`](booking-service/docs/domain-context.md),
   written with `documenting-domain-context`;
2. reviewed with `reviewing-code-by-aspect` across eleven aspects by clean-context reviewers, every critical and
   major checked by a clean-context verifier: the ledger is
   [`docs/review/review.md`](booking-service/docs/review/review.md), and its rendered page is
   [`docs/review/review.html`](booking-service/docs/review/review.html), published as the
   [live demo](https://si1verwind17.github.io/aspect-code-review/);
3. fixed in five commits, each aimed at named criticals, and after each one re-reviewed incrementally by fresh
   clean-context reviewers. Each review is one row of the ledger's History. The page's timeline steps through them
   hash by hash: the score change at each step, the findings that review resolved, and the ones it found in the
   fix.

Most findings are still open on purpose. **Do not deploy this code.**

Notes on how this copy was prepared, so the ledger reads correctly:

- The first review's hash, `4781c64`, refers to the service's own repository, which is not included here; its tree
  is the one this repository holds at `c51e603`. Every later hash in the ledger is a commit in this repository.
- Before the review, the previous review's ledger was removed, and two hazard lines that had marked its headline
  findings as accepted were taken out of the domain context, so the review had to find them again. The domain
  context's invariant I5 still points at one of those removed lines; the review reports that contradiction.
- The rendered views under `docs/review/` are committed here so they can be opened and published; in a normal
  repository they are regenerated from the ledger and not committed.
