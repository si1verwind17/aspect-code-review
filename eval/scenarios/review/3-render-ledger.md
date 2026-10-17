# Scenario 3: render the ledger for humans

Fixture and answer key: [`fixture.md`](fixture.md).

**Setup** (built by
[`build_s3_fixture.py`](../../fixtures/reviewing-code-by-aspect/build_s3_fixture.py) into `base-s3/`): a temp git
repo containing only `docs/review/review.md` — a
hand-authored ledger for a fictional billing service, built from
`template/review.md` in the template's own form (`---` rules,
`### <Aspect> (<ABBR>) — <score>/10 · <n> open` headers, summary rows in
catalog order), committed clean. It carries 16 aspects (the 15 catalog
aspects plus one custom, `API documentation (DOC)`, last), 16 open finding
IDs, scores spanning all three bands, a two-row history table, one archived
finding, and one credited-as-intentional entry. The fixture's minor-band
values (PAT 8.5, RDB 7.5) were authored under the earlier count-deducting
minor arithmetic and are kept as is: this scenario tests parsing — the
renderer takes scores from the summary table and never recomputes them.
Grading key (aspect → score):
LOG 6, ERR 5, SEC 3, PAT 8.5, CON 10, CMP 9, LGG 3, MEM 10, CPU 6, STA 10,
TST 10, TSQ 4, TYP 9, RDB 7.5, FMT 10, DOC 6 · average 7.3 · worst SEC/LGG.
The skill arm gets a copy of the whole skill folder at a neutral path outside the repo.

**Prompt** (identical for both arms; skill arm prepends "Read
<skill-copy>/SKILL.md first and follow it"; control arm prepends "Do NOT
load or read any skill, convention guide, or AGENTS.md from this
environment"):

> Turn docs/review/review.md into an HTML page a human can read at our
> release gate — the review scores should be visible as a chart, not just
> a table. Put the page next to the ledger.

**Checks** (PASS/FAIL per run):

1. Source untouched: `review.md` byte-identical after the run; no other
   tracked file modified.
2. Self-contained page: one HTML file (plus at most a `.gitignore`)
   beside the ledger; no external
   network dependency (no CDN script/stylesheet/font URLs); opens
   standalone from disk.
3. Faithful chart: a per-aspect score chart shows all 16 aspects with
   exactly the grading-key values — 16/16 correct, none dropped (a table
   restyled as HTML is not a chart).
4. Order preserved: chart rows/axes and any rendered score table keep the
   ledger's row order; sorting by score anywhere is a FAIL.
5. Thresholds encoded accessibly: the ship / schedule-fixes / do-not-ship
   bands are visible on the chart (boundaries at 3 and 8), and band
   identity is carried by more than color alone (position against drawn
   thresholds, icons, or text labels).
6. Fidelity beyond the chart: all 16 open finding IDs appear on the page;
   the page leads with the worst aspects (SEC/LGG at 3), and the 7.3
   average appears only as secondary/trend information — an average-led
   page is a FAIL.
7. Regeneration story: the page comes from a rerunnable generator (the
   skill's script or an equivalent the run produced) and carries a notice
   that it is generated from the markdown, which stays the source of
   truth; a hand-authored one-off HTML with no regeneration path is a
   FAIL.
8. History timeline: with more than one History row, the page provides a
   control to move between review points that re-targets the chart to
   that row's scores, and at a historic point does not present the
   latest open-finding list as that point's detail. Verified from the
   embedded data and script, not from the page's own claims.
