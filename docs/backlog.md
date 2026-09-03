# ReconAgent — Backlog

> Future / icebox items not scheduled for the current build phase. Pull into `tasks.md` when they become active. Phase P3 and future roadmap live here.

## Phase P3 — Stretch (only if time remains)

| Item | Cluster | Notes |
|---|---|---|
| Real-data texture layer (narration templates, realistic amounts) | A | Improves demo realism |
| Per-stage breakdown visualization polish | C | Beyond basic counts |
| Multi-bank-account scenario | A/B | Adds `bank_account_last4` routing |

## Future Roadmap (out of prototype scope — see `scope.md`)

| Item | Why deferred |
|---|---|
| Cross-border / forex reconciliation | Out of scope; dynamic rate drift |
| Multi-currency support | Out of scope; INR/paise only |
| ChromaDB vector clustering | Out of scope; string heuristics suffice at 50 records |
| Prometheus metrics export | Out of scope; JSON counters now |
| Continuous / real-time reconciliation | Batch prototype |
| Postgres migration | Documented upgrade path, not this build |

## Icebox / Ideas (not committed)

- Export audit trail to PDF/CSV for the demo narrative
- Confidence-tier histogram on the summary panel
- "Recurring same-root-cause" auto-suggested cluster labels

Anything pulled into active work: move to `tasks.md`, assign cluster, set status.
