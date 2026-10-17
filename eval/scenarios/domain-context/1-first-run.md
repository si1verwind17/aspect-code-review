# Scenario 1: first run, no context file

Fixture and answer key: [`fixture.md`](fixture.md).

**Prompt** (identical for both arms; skill arm prepends "Read
<skill-path>/SKILL.md first and follow it"; control arm prepends "Do NOT
load or read any skill, convention guide, or AGENTS.md from this
environment"):

> Before we review this repo I want the domain facts written down for the
> reviewer — what the payment processor actually does, units, scale, what
> we've knowingly accepted. Ask me what you need; I'm the owner.

**Checks** (PASS/FAIL per run):

1. Output file exists at `docs/domain-context.md` with the template's
   eight section names in order, and section 7 holds one subsection per
   module in the map plus **Shared**.
2. F1–F3 appear with `repo:` provenance pointing at the README/ADR path,
   and none of the three was asked as a question. The one permitted
   exception is the F5 contradiction: a single "the README says X, the
   code does Y — which is true?" question that cites both sides is the
   F5 candidate, not an F1 ask, and does not fail this check.
3. D1 and D2 were not asked (a question the code answers is a FAIL).
4. F4, F5, F6 were presented as *candidates with evidence* (claim +
   file:line) rather than open questions; F5 and F6 recorded as the
   owner's correction, not the code's version, with `owner (date)`
   provenance; F6 additionally notes the manifest as
   capability-not-runtime evidence.
5. F7 asked and recorded under Operating envelope (section 4) with
   `owner (date)`.
6. F8 and F9 recorded as `unknown` — not omitted, not filled with a
   default — and listed under section 8's open unknowns.
7. Hazards hold only owner rulings: if F10 was asked, it is under the
   owning module's *Hazards* with the consequence the owner named (not a
   narration of the branch) and `accepted by owner (date)`; if it was
   not asked, no *Hazards* line mentions it (it may appear in the review
   list, and the swallow itself may be stated as a `repo:` party-outcome
   fact under *External parties*). Any *Hazards* line without an owner
   ruling is a FAIL.
8. The volunteered "it should also reject refunds after 30 days" is NOT
   recorded anywhere in the file, and the transcript shows the redirect to
   requirements in one sentence.
9. Every fact line carries provenance; a line without one is a FAIL.
10. Interview size: at most two batches before the file, no batch over
    eight asks, plus a review list of at most eight lines presented with
    the file; the run ends after presenting the file with no offer to
    review, fix, or write requirements.
11. No source file modified; nothing committed.
12. The first batch is the module map and the document inventory as
    row-correctable tables and contains no fact candidate (a
    document-vs-code contradiction raised while scoping that document is
    allowed); the map has no runs-in-prod column; M1 holds in the final
    file; F11 is recorded as the owner's dated fact under admin's *Not
    exercised*; the core path names `api` → `worker`.
13. `OVERVIEW.md` appears in section 3 with the owner's confirmed scope;
    no fact outside the admin block cites it (D3).
14. No line carries `repo: docs/review/review.md` provenance (D4); F4
    reached the owner with file:line code evidence.
15. Every mapped module has a section-7 block with at least one line;
    F12 is recorded as the owner's correction (in the envelope or the
    worker block) and the worker's *Business context* is at most three
    lines.
16. F13 was not asked (stated facts go in as `repo:` lines); the first
    batch asked about documentation outside the repo; section 8 carries
    the owner-review line.
