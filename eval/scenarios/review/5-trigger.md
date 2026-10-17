# Scenario 5: a plain review request loads only the review skill

Does `documenting-domain-context` stay out of a review nobody asked it for? Its description says it runs only on
request; this scenario checks the harness agrees.

**Setup:** the scenario-1 fixture ([`fixture.md`](fixture.md)) with both skills installed project-locally
(`<repo>/.claude/skills/` holding `reviewing-code-by-aspect/` and `documenting-domain-context/`). One headless
session per rep, cut short once the review has started:

```
claude -p "<prompt>" --model sonnet --max-turns 8 --output-format stream-json --verbose
```

**Prompt:**

> Review this repository's code quality. I want a concrete, documented result I can act on — including scores.

**Checks** (from the session's tool calls):

1. The `Skill` tool loads `reviewing-code-by-aspect`.
2. No tool call loads or reads `documenting-domain-context` (its `SKILL.md` or template).
3. No question about domain context, scale or business facts reaches the user before the review starts.
