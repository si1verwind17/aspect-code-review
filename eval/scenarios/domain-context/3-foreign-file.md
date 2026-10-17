# Scenario 3: foreign file at the path

Fixture and answer key: [`fixture.md`](fixture.md).

**Setup:** the repo already has a `docs/domain-context.md` that is a
hand-written prose page about the product (not this format), committed
as a second fixture commit; "nothing committed" means no commit beyond
the fixture's own.

**Prompt:** as scenario 1.

**Checks:**

1. The existing file is byte-identical after the run.
2. Facts it states appear in the new file with `repo:` provenance —
   to the prose page or to the primary source it restates — and were
   not asked.
3. The agent asked for an output path exactly once and wrote there.
