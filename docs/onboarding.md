# ReconAgent — Onboarding

> How a new agent (or human) gets up to speed fast. Single-owner project, but future session/agent must not re-derive context.

## Fast Path (5 min)

1. Read **`master-design.md`** — the single ultimate source of truth. Everything lives there.
2. Read **`decisions.md`** — the 8 locked decisions. Do not re-litigate.
3. Read **`scope.md`** — know what you must NOT build (ChromaDB, Prometheus, cross-border, multi-currency, real-time).

## Deeper Path (30 min)

4. `architecture.md` — components, data flow, boundaries
5. `data-sources.md` — synthetic ground truth + hidden answer key
6. `taxonomy.md` — reason codes, confidence tiers, event types, metrics (canonical vocabulary)
7. `flow.md` — build order P0→P1→P2
8. `constraints.md` — hard limits
9. `tech-stack.md` — what tools, why

## Working Loop

- **Tasks**: current work lives in `tasks.md`; icebox in `backlog.md`.
- **Changing anything**: update the relevant doc + append to `changelog.md`. Never edit old changelog/review-log entries.
- **Conflict**: see `sources-of-truth.md` (ranked precedence; master-design.md wins).
- **Blocked / ambiguous**: ask the human before acting.

## Guardrails Summary

- Never let `answer_key.json` reach the matcher.
- Never `UPDATE` exception status in place — append events.
- Stage 5 LLM is last resort, async, structured output, never sole authority.
- Maker proposes; only Checker closes books.

## Repro the state in 3 commands (once code exists)

Generate → Run → Report (see `architecture.md` data flow). Until code exists, the docs set above is the artifact.
