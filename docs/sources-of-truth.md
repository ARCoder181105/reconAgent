# ReconAgent — Sources of Truth

> Ranked precedence: which file wins when two conflict. The Master Design Document is the ultimate source of truth.

## Ranked Precedence (highest wins)

1. **`master-design.md`** — The ultimate source of truth. Contains the full architecture, schema, pipeline, and future scope. Any doc that contradicts it is wrong.
2. **`decisions.md`** — Locked decisions that the whole project obeys. Cannot be silently overridden.
3. **`constraints.md`** — Hard limits (break nothing in the non-negotiable list).
4. **`taxonomy.md`** — Canonical reason codes, confidence tiers, stage keys, event types, metric definitions. Single vocabulary.
5. **`scope.md`** — In/out of scope boundary.
6. **`glossary.md`** — Locked term definitions.
7. **`sources-of-truth.md`** (this file) — Resolution rules.
8. **`conventions.md`** — Naming/structure/style, overridden by any of the above.
9. **Supporting design docs** — `architecture.md`, `data-sources.md`, `tech-stack.md`, `flow.md` — consistency only; defer to the above on conflict.
10. **Process / ephemeral docs** — `tasks.md`, `backlog.md`, `changelog.md`, `assumptions.md`, `risks.md`, `review-log.md`, `onboarding.md`, `ownership.md` — cheapest to change; never authoritative for design truth.

## Conflict-Resolution Rule

If two docs disagree on a *design* fact (architecture, schema, reason codes, locked decision, scope, constraint), the higher-ranked doc wins. If a *lower*-ranked doc is right and a higher one is stale, that is itself a defect — record it in `tasks.md` and fix the higher doc, then `changelog.md`. Do not silently act on the lower doc.

## The Hidden Answer Key

`answer_key.json` is the source of truth for **scoring only** (ground truth). The matcher never reads it. Its precedence applies solely inside the offline scoring path.

## When In Doubt

Ask the human maintainer. Single-owner project — the human is the final arbiter over all docs.
