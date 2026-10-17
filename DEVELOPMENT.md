# Development

## Layout

| Path | What it is |
|---|---|
| `skills/<name>/` | The skills as installed: one `SKILL.md` each, plus the files it reads |
| `demo/booking-service/` | One full review with its domain context, committed verbatim: a showcase for people, published to GitHub Pages by `.github/workflows/pages.yml`. Agents never read it |
| `eval/` | Agent evaluations: the protocol and latest results (`README.md`), one file per scenario under `scenarios/`, fixture builders and judge keys under `fixtures/` |
| `tools/lint.py` | Manifest, frontmatter and private-terms checks (stdlib only; CI runs it) |

## After a change

- Run `python3 tools/lint.py`.
- **Adding a skill:** add it to the `skills` list in `.claude-plugin/marketplace.json` and to the README.
- **Agent behaviour:** run the scenarios under `eval/scenarios/` the change touches, per [`eval/README.md`](eval/README.md),
  and replace that scenario's row under **Latest results**. An edit not yet run goes under **Pending validation**.
- **A release:** bump `version` in `.claude-plugin/marketplace.json` (both places).
