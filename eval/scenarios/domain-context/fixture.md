# Fixture: documenting-domain-context

Shared by every domain-context scenario: the fixture, the simulated owner and the hidden fact sheet judges grade against.

Fixture: a small synthetic payments gateway (~12 files, one language) in a
temp git repo, sitting between one merchant platform and one card
processor, laid out as three modules — `api/` (payment intake, core
path), `worker/` (settlement job, core path), `admin/` (internal admin
UI, wired into the compose file but not deployed) — over a shared schema
in `common/`, plus `deploy/` (compose file, deploy script) and `scripts/`
(a one-off research notebook). It ships a README that documents two facts
well, an ADR that documents one, a root-level `OVERVIEW.md` generated for
the admin module alone (it describes the admin UI and states "payments
are settled every 5 minutes", which predates the worker), a prior review
ledger at `docs/review/review.md` whose declared assumptions include
"authorizations always succeed or decline immediately" (wrong — see F4),
and code that makes six further facts *plausible but unconfirmed*.
The **owner is simulated** from a hidden fact sheet: a separate model call
per owner message (an `ask-owner` script the runner may invoke but must
not read; the sheet lives base64-encoded in a sibling dotfile, never in
the script body — a runner that reads the script to learn its usage must
see nothing). It answers only questions actually asked, in one line each,
answers "unknown" for two facts on the sheet marked unknown, and — once,
in its first reply — volunteers an intended-behavior sentence ("it should
also reject refunds after 30 days") to test the requirements redirect.
The volunteer line is written into the persona ("you are the kind of
owner who tacks on…"), not as a separate instruction the model can
refuse as an injection. Judges grade against the sheet, not their own
taste, and record a FIXTURE NOTE when the owner breaks character or
deviates from the sheet. Harness rules learned the hard way: the sheet
dotfile must be **untracked and gitignored**, or an update-mode runner's
scoping `git diff` prints it; the simulated owner drifts under long
multi-question messages (control arms especially), so the sheet routes
every phrasing of replicas, throughput and hazard-acceptance questions
to a fixed answer; **each answer names only the fact asked** — the F5
answer never states the fee rate, the F12 answer never adds the pending
expiry, a document-scope answer never adds facts from that document — or
the runner records a documented fact as the owner's and the checks for
F1 and F4 measure the sheet, not the skill; the S2 sheet must never tell
the owner to say "that's already in the file" — it says it for lines
that are not; and the hand-authored S2 context file must match the key
exactly (core path `api → worker`, the processor being an external
party) or the agent is penalised for correcting the fixture.

Builder: [`eval/fixtures/documenting-domain-context/build_fixture.py`](../../fixtures/documenting-domain-context/build_fixture.py)
writes the scenario-1 repo and its owner (`ask-owner`, with the sheet in the gitignored
`.owner-sheet`) to `base/` beside itself; copy `base/` per run, dotfiles included, and delete
`.owner-transcript.jsonl` to reset the owner. Judges grade with
[`key.md`](../../fixtures/documenting-domain-context/key.md); runners never see it.

Hidden fact sheet (answer key):

- F1 (README, documented): the processing fee is 2.9% of the captured
  amount. — the agent must cite the README, not ask.
- F2 (README, documented): the service runs single-tenant (one merchant
  platform per deployment). — cite, not ask.
- F3 (ADR-003, documented): the idempotency key is `idempotency_key`.
  — cite.
- F4 (code-plausible): a payment the processor accepts can stay
  `PENDING` (asynchronous authorization) until a later status poll; the
  code stores `PENDING` and the worker polls it and expires it after 7
  days. Owner: confirm.
- F5 (code-plausible): on a cross-currency payment the code takes the fee
  in the card currency, while the README says the settlement currency.
  Owner: correct — "in the settlement currency when the merchant holds a
  settlement account in it, card currency otherwise; prod holds none".
  The owner sheet must give this answer *however* the fee currency is
  asked — as a card-currency confirm, as a README-vs-code "which is
  true", or as a fee question — must never say "the README is right", and
  must never state the rate; a sheet keyed only to one phrasing drifts.
- F6 (code-plausible, wrong): the code's `replicas: 3` manifest. Owner:
  correct — "prod runs one replica; the manifest is a template".
- F7 (code cannot answer): throughput. Owner: "~40 payments/min peak".
- F8 (code cannot answer): whether the processor actually executes a
  scheduled capture (a `capture_at` date sent with the payment). Owner:
  unknown.
- F9 (code cannot answer): who bears the refund fee. Owner: unknown.
- F10 (hazard): metrics emission failures are swallowed. The code states
  the swallow; whether it is accepted cannot be inferred. Owner, when
  asked: accepted, consequence "dashboards lag, payments unaffected". If
  the agent never asks (batch 2 full, review list unanswered), the
  hazard must NOT appear in the file at all.
- F13 (stated — must NOT be asked): the processor retry count and timeout
  are constants in `common/config.py`. They appear in the file with `repo:`
  provenance; putting them to the owner as a question is a FAIL.
- F11 (code-plausible, wrong): the compose file wires `admin/`, so the
  map candidate reads as a deployed module. Owner: correct — "admin is a
  local tool, not deployed". Role stays supporting; the fact lands under
  admin's *Not exercised* with `owner (date)`.
- M1 (module split): the final map holds exactly `api`, `worker`,
  `admin`; `common` appears only as the **Shared** block; `deploy/` and
  `scripts/` are not rows. The owner rejects them if offered ("not
  modules, that's deploy and misc").
- F12 (code cannot answer): the worker's cadence — the README says
  nightly, the code reads it from an env var not in the repo. Owner:
  correct — "hourly", and nothing more.
- D1 (decoy — answerable from code): what database the service uses.
  Asking it is a FAIL.
- D2 (decoy — answerable from code): which HTTP client library is used.
  Asking it is a FAIL.
- D3 (decoy — document scope): `OVERVIEW.md`. Its scope must be presented
  as a candidate in the first batch; owner: "admin UI only, written before
  the worker existed". Citing it for any fact outside the admin module,
  or asking about the 5-minute cadence as if it were a system fact, is a
  FAIL.
- D4 (decoy — prior review ledger): `docs/review/review.md`. Any fact
  carrying `repo: docs/review/review.md` provenance is a FAIL; its
  authorization assumption reaches the owner only as the F4
  code-evidenced candidate.
