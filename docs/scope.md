# ReconAgent — Scope

> What is in, what is out. Source: `master-design.md`.

## In Scope

- Multi-source reconciliation of Razorpay-style settlement report vs messy bank statement (single INR merchant account)
- Staged 5-pipeline matching engine (deterministic Stages 1–4 + async LLM Stage 5)
- Honest exception queue with reason codes, confidence, and ranked candidates
- Lightweight exception clustering via reason code + string heuristics (powers Bulk Resolve)
- Maker-Checker manual workflow
- Event-sourced, append-only exception audit log
- Synthetic data generator with hidden answer key
- Offline precision/recall scoring (offline, never in engine)
- React dashboard: summary, exception queue, audit trail, data inspection, Pending Approval tab
- FastAPI REST backend + SQLite persistence

## Out of Scope (explicitly excluded from prototype)

These are future roadmap items (see `master-design.md` §17), deliberately **not** part of the core build:

| Excluded | Reason |
|---|---|
| Cross-border payments / forex drift / SWIFT refs | Foreign to INR/UTR scope; adds unpredictable amount drift |
| Multi-currency | Schema is INR/paise-integer only |
| ChromaDB / vector embeddings for clustering | Overkill at 50 records; string heuristics suffice (future only) |
| Prometheus / metrics-server telemetry | Lightweight JSON counters instead (prototype) |
| Real-time / continuous reconciliation | Batch-only for the prototype |
| Real merchant / bank records | Synthetic ground-truth only; no row-level real financial data |
| Multi-bank-account routing layer | Only single merchant account |
| Postgres | SQLite now, Postgres is a documented upgrade path only |

## Guardrail

If scope creep is proposed mid-build, route it through the re-litigation policy in `decisions.md` and confirm it does not violate an out-of-scope exclusion before any work.
